"""Génération du carrousel Instagram via Gemini 3 Pro Image.

Format : 1080x1350 (portrait 4:5, feed Instagram).
Style : même design system cyan magazine que les infographies OpenAI.
Sortie : liste de chemins locaux vers les PNG (1 par slide).

Gemini ne supporte pas 1080x1350 nativement (ses sorties sont 1024x1024, 1024x1536,
1536x1024). On génère en 1024x1536 puis on crop au ratio 1080x1350 ≈ 4:5 via Pillow.
"""
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from PIL import Image

from config.settings import DATA_DIR, GEMINI_API_KEY, GEMINI_IMAGE_MODEL

logger = logging.getLogger(__name__)

CAROUSEL_DIR = DATA_DIR / "carousels"
CAROUSEL_DIR.mkdir(exist_ok=True)

# Ratio Instagram feed 4:5 = 1080:1350. Après génération 1024x1536 Gemini,
# on crop à 1024 x (1024 * 5/4) = 1024x1280 (centré vertical).
TARGET_RATIO = 4 / 5  # width / height


# --------------- Templates par type de slide ---------------

COVER_PROMPT = """A premium editorial Instagram carousel cover slide, portrait 4:5 ratio, French, magazine-style.

FULL BLEED: warm cream #F5F0E8 background edges to all four corners. No white border anywhere.

LAYOUT:
- Top ~15%: small thin-line cyan #5CE1E6 asterisk icon at top-left, and date "{DATE}" in small cyan uppercase letter-spaced, top-right.
- Center ~55%: a massive heavy serif ALL CAPS title occupying most of the slide. Two stacked lines, bold black #1A1A1A, tight tracking. Render EXACTLY:
  Line 1: "{TITLE_MAIN}"
  Line 2: "{TITLE_SUB}"
- Below title, ~20%: a horizontal cyan #5CE1E6 thin line (1 px), then the hook text in medium sans-serif, black, max 2 lines. Render EXACTLY: "{HOOK}"
- Bottom ~10%: a thin horizontal cyan line, then centered "VEILLE IA" in small cyan uppercase letter-spaced.

COLORS (strict): cream #F5F0E8 background, cyan #5CE1E6 accent, black #1A1A1A text. No other color.
TYPOGRAPHY: heavy serif (Tiempos Headline Black style) for the title, clean sans-serif (Söhne style) for the hook.
FORBIDDEN: no photo, no 3D, no emoji, no gradient, no shadow, no em dash, no missing French accents.

The cover must feel like a premium editorial magazine cover, NOT an auto-generated social post."""


NEWS_PROMPT = """A premium editorial Instagram carousel slide, portrait 4:5 ratio, French, magazine-style.

FULL BLEED: warm cream #F5F0E8 background edges to all four corners. No white border anywhere.

LAYOUT for this NEWS slide:
- Top ~10%: the slide number "{NUMERO}" in small cyan #5CE1E6 italic serif at top-left, and the source "{SOURCE}" in small black uppercase letter-spaced at top-right.
- A thin horizontal cyan #5CE1E6 line below (1 px), full width minus 50-64 px margins.
- Middle ~55%: a large heavy serif ALL CAPS title, black #1A1A1A, max 3 lines, tight tracking. Render EXACTLY: "{TITLE}"
- ~15% below title: the editorial hook in medium sans-serif black, 2-3 lines max, with NO ALL CAPS. Render EXACTLY: "{HOOK}"
- Right side (if STAT present, ~25% width): a vertical white #FFFFFF card with 1 px cyan border. Inside: micro cyan label "STAT" at top, large cyan #5CE1E6 number "{STAT}" in middle. Only render this card if STAT is not empty.
- Bottom ~10%: a thin horizontal cyan line, then the text "VEILLE IA" in small cyan uppercase letter-spaced on the left, and the slide number indicator "{NUMERO}" in small black on the right.

COLORS (strict): cream #F5F0E8 background, cyan #5CE1E6 accent, black #1A1A1A text, white #FFFFFF for the stat card only.
TYPOGRAPHY: heavy serif (Tiempos Headline Black style) for the title, clean sans-serif (Söhne style) for hook and labels.
FORBIDDEN: no photo, no 3D, no emoji, no gradient, no shadow, no em dash, no missing French accents.

STAT INFO (only render the stat card if present): {STAT_CARD_INSTRUCTIONS}

The slide must look like a premium editorial magazine page, each slide of a cohesive carousel with consistent visual language."""


OUTRO_PROMPT = """A premium editorial Instagram carousel outro slide, portrait 4:5 ratio, French, magazine-style.

FULL BLEED: warm cream #F5F0E8 background edges to all four corners. No white border anywhere.

LAYOUT:
- Top ~15%: small thin-line cyan #5CE1E6 heart icon at top-left, and date "{DATE}" in small cyan uppercase letter-spaced, top-right.
- Center ~50%: a massive heavy serif ALL CAPS title. Two stacked lines, bold black #1A1A1A, tight tracking. Render EXACTLY:
  Line 1: "{TITLE_MAIN}"
  Line 2: "{TITLE_SUB}"
- Below ~15%: a horizontal cyan line, then hook text in medium sans-serif black, max 2 lines. Render EXACTLY: "{HOOK}"
- Bottom ~20%: a large cyan #5CE1E6 rectangular button with 8 px corner radius, containing in white ALL CAPS bold sans-serif: "RETROUVEZ LA VEILLE CHAQUE MATIN". Below the button, small cyan uppercase letter-spaced text "VEILLE IA DU {DATE}".

COLORS (strict): cream #F5F0E8 background, cyan #5CE1E6 accent, black #1A1A1A text, white on cyan for the button.
TYPOGRAPHY: heavy serif for title, clean sans-serif for button and hook.
FORBIDDEN: no photo, no 3D, no emoji, no gradient, no shadow, no em dash, no missing French accents."""


# --------------- API publique ---------------


def generate_carousel_images(carousel: dict[str, Any]) -> list[str]:
    """Génère toutes les slides du carrousel et retourne la liste des chemins locaux.

    L'ordre est : cover, slide 01, slide 02, ..., outro.
    """
    if not carousel:
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)
    today = datetime.now().strftime("%Y%m%d")
    paths: list[str] = []

    # 1. Cover
    paths.append(_render_slide(client, _build_cover_prompt(carousel["cover"]), today, 0, "cover"))

    # 2. N slides news
    for i, slide in enumerate(carousel["slides"], start=1):
        paths.append(_render_slide(client, _build_news_prompt(slide), today, i, "news"))

    # 3. Outro
    paths.append(
        _render_slide(
            client, _build_outro_prompt(carousel["outro"]), today, len(carousel["slides"]) + 1, "outro"
        )
    )

    paths = [p for p in paths if p]
    logger.info(f"Carrousel généré : {len(paths)} slides")
    return paths


# --------------- Prompt builders ---------------


def _build_cover_prompt(cover: dict[str, Any]) -> str:
    return (
        COVER_PROMPT.replace("{DATE}", cover.get("date", ""))
        .replace("{TITLE_MAIN}", cover.get("title_main", ""))
        .replace("{TITLE_SUB}", cover.get("title_sub", ""))
        .replace("{HOOK}", cover.get("hook", ""))
    )


def _build_news_prompt(slide: dict[str, Any]) -> str:
    stat = slide.get("stat", "")
    stat_instructions = (
        "Render the stat card described above with the STAT number shown."
        if stat
        else "No stat card for this slide. Do not render a stat card. The title and hook fill the available space."
    )
    return (
        NEWS_PROMPT.replace("{NUMERO}", slide.get("numero", ""))
        .replace("{SOURCE}", slide.get("source", ""))
        .replace("{TITLE}", slide.get("title", ""))
        .replace("{HOOK}", slide.get("hook", ""))
        .replace("{STAT}", stat or "")
        .replace("{STAT_CARD_INSTRUCTIONS}", stat_instructions)
    )


def _build_outro_prompt(outro: dict[str, Any]) -> str:
    return (
        OUTRO_PROMPT.replace("{DATE}", outro.get("date", ""))
        .replace("{TITLE_MAIN}", outro.get("title_main", ""))
        .replace("{TITLE_SUB}", outro.get("title_sub", ""))
        .replace("{HOOK}", outro.get("hook", ""))
    )


# --------------- Rendering + post-process ---------------


def _render_slide(client: genai.Client, prompt: str, date_str: str, idx: int, kind: str) -> str:
    """Génère une image Gemini, crop au ratio 4:5, sauvegarde en PNG."""
    try:
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                cropped = _crop_to_4_5(part.inline_data.data)
                filename = f"{date_str}_carousel_{idx:02d}_{kind}.png"
                path = CAROUSEL_DIR / filename
                with open(path, "wb") as f:
                    f.write(cropped)
                logger.info(f"  Slide {idx:02d} ({kind}) -> {path}")
                return str(path)
        logger.warning(f"  Slide {idx:02d} ({kind}) : pas d'image dans la réponse")
        return ""
    except Exception as e:
        logger.error(f"  Slide {idx:02d} ({kind}) échec : {type(e).__name__} : {e}")
        return ""


def _crop_to_4_5(image_bytes: bytes) -> bytes:
    """Crop une image Gemini (souvent 1024x1536) au ratio 4:5, centré."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    target_h = int(w / TARGET_RATIO)
    if target_h <= h:
        # Centrer verticalement, crop haut/bas
        top = (h - target_h) // 2
        img = img.crop((0, top, w, top + target_h))
    else:
        # L'image est plus carrée que 4:5, on crop en largeur
        target_w = int(h * TARGET_RATIO)
        left = (w - target_w) // 2
        img = img.crop((left, 0, left + target_w, h))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
