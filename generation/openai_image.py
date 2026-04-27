"""Génération d'images via OpenAI gpt-image-2 (Image API).

Doc API : https://developers.openai.com/api/docs/models/gpt-image-2
Format unique : infographie magazine cyan style Monocle/Kinfolk.

Le prompt template est entièrement en anglais (instructions au modèle) mais
le contenu rendu sur l'image est en français.
"""
import base64
import io
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List

from openai import OpenAI
from PIL import Image

from config.models import NewsItem
from config.settings import DATA_DIR, OPENAI_API_KEY, OPENAI_IMAGE_MODEL
from observability.api_logger import log_api_call

logger = logging.getLogger(__name__)

IMAGES_DIR = DATA_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)


# Template d'infographie magazine cyan, optimisé pour gpt-image-2.
# Reprend strictement les specs visuelles validées par Brice (exemples 1, 2, 3).
PROMPT_TEMPLATE = """ASPECT RATIO: vertical 2:3, 1024x1536 pixels. Apply this ratio before composing anything.

ROLE
You are a senior art director for a contemporary print magazine. Your work has been published by Apple, Stripe, Linear. You do NOT generate images like a slot machine. You work like a designer who researches, analyzes, then composes with intent. You master Refactoring UI: hierarchy through size AND contrast (never color alone), generous whitespace, strict 8px grid alignment, disciplined type system.

TASK DECOMPOSITION, execute in this order before rendering
1. READ the full content brief below (title, subtitle, keywords to highlight, stat, 6 blocks). Identify the editorial logic: what is the main idea, what is the reading order, what is the visual climax.
2. PLAN the composition mentally: where each element sits in the 1024x1536 canvas, what relative sizes create the hierarchy, what icon fits each block topic.
3. RENDER the final poster, respecting every constraint below.

This is not optional. A poster generated without step 1 and 2 will look auto-generated. A poster with them will look art-directed.

TEXT RENDERING, ABSOLUTE RULES
Every text string in this prompt, whether between quotes or inside {placeholders}, must be rendered EXACTLY as written. Do not add words. Do not remove words. Do not paraphrase. Do not change spelling. Do not substitute accented characters (é è ê ë à â ç ï î ô û ù œ) with their unaccented versions. Do not insert em dashes (—) anywhere, use periods or commas instead. French orthography is perfect or the output is rejected.

FULL BLEED OUTPUT, CRITICAL
The cream background #F5F0E8 extends to ALL FOUR edges of the 1024x1536 image. The very first column of pixels (x=0), the very last column (x=1023), the very first row (y=0), the very last row (y=1535) are all cream #F5F0E8, NEVER white. Zero white border. Zero frame. Zero outer padding of any other color. Think of a printed magazine page where the ink goes to the paper edge. Internal content margins (50-80 px from image edges to the first text or block) are themselves cream, not white.

DESIGN SYSTEM, NON-NEGOTIABLE

Color palette, exactly these five hex values, nothing else:
- Warm cream paper #F5F0E8 for background, edge to edge
- Bright aqua cyan #5CE1E6 for: header bars, icon accent circles, keyword highlights inside subtitle, 1px thin borders, callout label text, footer line and icon
- Near-black #1A1A1A for body text, serif numerals, bullet text
- Pure white #FFFFFF for inner content block backgrounds
- Light cream #FAF6EF for callout boxes inside blocks

Mental check before rendering: every visible color on the final image must be one of those five. If you catch yourself adding a gradient, a glow, a second cyan, a neon, a drop shadow beyond 4% opacity, STOP and remove it.

Typography, max 2 type families:
- Main title: heavy contemporary serif, ALL CAPS, 72-96 pt equivalent, tight tracking, strong stroke contrast. References: Tiempos Headline Black, Domaine Display Black, Canela Bold, GT Sectra Display Bold.
- Block numerals "01" "02" "03" "04" "05" "06": same serif family in italic, 40-56 pt, color #1A1A1A. References: Tiempos Italic, Domaine Display Italic.
- Section titles inside cyan header bars: heavy sans-serif, ALL CAPS, white, tight tracking, 16-20 pt. References: Söhne Halbfett, GT America Bold, Inter Tight Bold.
- Body and bullet points: clean modern sans-serif, #1A1A1A, line-height 1.4, 11-14 pt. References: Söhne Buch, GT America Regular, Inter Tight Regular.
- Keyword highlights inside subtitle: same sans-serif, cyan #5CE1E6 inline, no underline, no background.
- Micro labels ("EXEMPLE :", "STAT", "RESULTAT :"): 9-10 pt cyan #5CE1E6 sans-serif ALL CAPS, letter-spacing ~0.1 em.

Spacing, strict 8px grid:
- Cream #F5F0E8 full bleed on all four edges. No white frame around the poster, ever.
- Inside the full-bleed cream, the design blocks start at 50-64 px from the left cream edge and end 50-64 px before the right cream edge, floating on cream.
- Horizontal gutter between the two columns of blocks: 32-40 px.
- Vertical gap between block rows: 24-32 px.
- Inner padding inside white content blocks: 18-24 px.
- Vertical breathing room above and below the main title: 48 px minimum.
- Refactoring UI rule: when in doubt, add more space. Whitespace beats decoration.

Visual hierarchy, exactly 3 levels:
Level 1, one single dominant element: the main title. It is the first thing the eye catches in under 0.5 seconds.
Level 2: the section titles inside cyan header bars.
Level 3: bullet text and callouts.
Hierarchy is achieved through SIZE and WEIGHT, never through bright colors. No more than 3 levels on the entire poster.

Icons:
Every icon on the poster comes from the same thin-line monochrome family, 1.5 pt stroke, no fill, identical visual weight, identical scale within its role. Pick each block icon from this closed set based on topic relevance: lightbulb, brain, puzzle piece, document, balance scale, target, rocket, gear, magnifying glass, chat bubble, chart bars, shield, compass, megaphone, key. No emoji. No 3D icon. No gradient icon.

Forbidden elements, zero exceptions:
No photograph, no realistic person, no AI-generated face, no emoji anywhere, no 3D illustration, no gradient, no glow, no neon, no drop shadow above 4% opacity, no em dash.

LAYOUT STRUCTURE, precise placement

Top header zone, ~18% of poster height, rows 0 to ~275:
- Top left corner of the content area (not the image edge, the content area 50-64 px inside): a thin-line cyan #5CE1E6 6-pointed asterisk icon, 1.5 pt stroke, no fill, small but visible. Vertically centered with the main title baseline.
- Main title: MASSIVE heavy serif ALL CAPS, color #1A1A1A, occupying ~70% of the header row width, aligned to the left. Render the title text EXACTLY as: "{TITRE}". If the title is shorter than 15 characters, scale it up further. If longer, allow two lines with tight leading.
- Subtitle placed directly below the main title, medium-size sans-serif, color #1A1A1A. Render the subtitle text EXACTLY as: "{SOUS_TITRE}". Inside this subtitle, the following exact words must appear in cyan #5CE1E6 inline color (same size, no underline, no background): {KEYWORDS_CYAN_LIST}.
- Top right corner of the content area: a vertical rectangular card, width ~25% of poster width, height covering most of the header zone, white #FFFFFF background, 1 px thin cyan #5CE1E6 border, no shadow. Inside the card, from top to bottom:
  * Micro label at the top: "STAT" in cyan ALL CAPS, letter-spaced, 9-10 pt.
  * Center of the card: very large cyan #5CE1E6 numerals or letters, heavy weight, taking most of the card vertical space. Render exactly: "{STAT}".
  * Bottom of the card: caption in small near-black sans-serif, maximum 2 lines. Render exactly: "{STAT_DESC}".

Main body zone, ~75% of poster height, rows ~275 to ~1420:
A perfect 2-column grid of numbered content blocks. Left column contains blocks 01, 02, 03 from top to bottom. Right column contains blocks 04, 05, 06 from top to bottom. Columns have identical width. Gutter between columns: 32-40 px. Vertical gap between block rows: 24-32 px. Every block has IDENTICAL height to its neighbors, strict magazine grid alignment.

Every block is built from three stacked zones, top to bottom:

Zone A, block header bar, ~52 px tall:
Solid cyan #5CE1E6 horizontal bar, full block width, no border. Internal padding 16-20 px. Three elements aligned horizontally on the same baseline:
- Left ~15% of bar width: the block numeral ("01", "02", "03", "04", "05", "06") in heavy serif italic, color white, vertically centered.
- Center ~70% of bar width: the block title in heavy sans-serif ALL CAPS, color white, tight tracking, vertically centered.
- Right ~15% of bar width: a single thin-line monochrome white icon, 1.5 pt stroke, no fill, ~22 px, chosen from the icon set above based on block topic. Vertically centered.

Zone B, block content area:
White #FFFFFF background, framed by 1 px thin cyan #5CE1E6 border on all four sides, internal padding 18-24 px. Contains 3 to 4 bullet rows. Each bullet row is built as: a small filled cyan #5CE1E6 disc (6 px diameter) aligned to the left, then a small gap (~8 px), then the bullet text in near-black #1A1A1A sans-serif. Each bullet fits on one line ideally, two lines maximum if absolutely necessary. Line-height 1.4.

Zone C, bottom callout, optional per block:
If a callout is present for the block, render a full-width strip with light cream #FAF6EF background, framed by 1 px thin cyan #5CE1E6 border on all four sides, internal padding 12-16 px. First line: a micro label in cyan ALL CAPS letter-spaced ("EXEMPLE :" or "RESULTAT :" as specified per block). Following lines: the example or result sentence in near-black italic sans-serif.

The exact content of all six blocks follows. Render the French text word-for-word, respecting every accent:

{BLOCS_FORMATTED}

Footer zone, ~7% of poster height, rows ~1420 to 1536:
- A thin horizontal cyan #5CE1E6 line, 1 px, spanning the full content width (not the full image width, respect the 50-64 px content margins left and right).
- Below the line, horizontally centered in the content area: a thin-line cyan #5CE1E6 heart icon, 1.5 pt stroke, no fill, ~14 px, followed by a small gap (~8 px), followed by the text "SAUVEGARDEZ ET PARTAGEZ" in cyan #5CE1E6 ALL CAPS sans-serif, small size 10-11 pt, generous letter-spacing ~0.15 em.

OBEDIENCE TEST, the model must pass all ten before rendering
This list exists because GPT-Image 2 obeys precise instructions but only if they are precise. Verify each point mentally, then render.
1. Aspect ratio is exactly 2:3, exactly 1024 x 1536 pixels.
2. The four image edges (row 0, row 1535, column 0, column 1023) are cream #F5F0E8, not white, not beige, not off-white.
3. The main title is in position 1 of visual hierarchy. Nothing else on the poster is bigger or heavier.
4. The top right card exists, contains the "STAT" label, the {STAT} value in large cyan, and the {STAT_DESC} caption.
5. Exactly 6 content blocks are rendered, arranged in a 2 by 3 grid (2 columns, 3 rows). All blocks have identical height.
6. Each block has a cyan header bar with numeral + title + icon, a white content area with bulleted list, and optionally a cream callout at the bottom.
7. All icons share the same thin-line monochrome 1.5 pt family, no fill.
8. Every French accented character is correctly rendered. No character is substituted, dropped, or replaced by a similar Latin character.
9. No em dash (—) appears anywhere in the rendered text. No emoji. No photo. No realistic face. No gradient.
10. The composition feels airy, deliberately spaced, art-directed. Not auto-generated.

If any of the ten points fails, the render is rejected. The model is not making decorative art. It is executing a magazine art director's brief.
"""


def generate_images(items: List[NewsItem]) -> List[NewsItem]:
    """Génère une infographie par news avec OpenAI gpt-image-2."""
    if not items:
        return []

    client = OpenAI(api_key=OPENAI_API_KEY)
    today = datetime.now().strftime("%Y%m%d")

    for i, item in enumerate(items):
        if not item.structured_content:
            logger.warning(f"Pas de contenu structuré pour : {item.title[:60]}, skip")
            continue

        t0 = time.perf_counter()
        try:
            logger.info(f"Génération image {i+1}/{len(items)} : {item.title[:60]}")

            prompt = _build_prompt(item.structured_content)
            item.image_prompt = prompt
            logger.info(f"  Prompt longueur : {len(prompt)} chars")

            response = client.images.generate(
                model=OPENAI_IMAGE_MODEL,
                prompt=prompt,
                size="1024x1536",
                quality="high",
                output_format="png",
                background="opaque",
                moderation="auto",
                n=1,
            )
            log_api_call(
                provider="openai",
                model=OPENAI_IMAGE_MODEL,
                operation="images.generate",
                duration_ms=int((time.perf_counter() - t0) * 1000),
                success=True,
                context={"step": "image_generation", "news_title": item.title[:60]},
            )

            image_b64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_b64)

            # Post-process : crop les marges blanches laissées par gpt-image-2
            image_bytes = _crop_white_borders(image_bytes)

            filename = f"{today}_{i+1:02d}_infographie.png"
            image_path = IMAGES_DIR / filename
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            item.image_path = str(image_path)
            logger.info(f"  Image sauvegardée : {image_path}")

        except Exception as e:
            log_api_call(
                provider="openai",
                model=OPENAI_IMAGE_MODEL,
                operation="images.generate",
                duration_ms=int((time.perf_counter() - t0) * 1000),
                success=False,
                error=str(e),
                context={"step": "image_generation", "news_title": item.title[:60]},
            )
            logger.error(f"Erreur génération image '{item.title[:60]}' : {type(e).__name__} : {e}")

    return [item for item in items if item.image_path]


def _build_prompt(content: dict[str, Any]) -> str:
    """Injecte les variables structurées dans le template prompt."""
    return (
        PROMPT_TEMPLATE.replace("{TITRE}", content.get("titre", ""))
        .replace("{SOUS_TITRE}", content.get("sous_titre", ""))
        .replace("{KEYWORDS_CYAN_LIST}", _format_keywords(content.get("keywords_cyan", [])))
        .replace("{STAT}", content.get("stat", "NOUVEAU"))
        .replace("{STAT_DESC}", content.get("stat_desc", ""))
        .replace("{BLOCS_FORMATTED}", _format_blocs(content.get("blocs", [])))
    )


def _format_keywords(keywords: list[str]) -> str:
    if not keywords:
        return "(no specific keywords)"
    if len(keywords) == 1:
        return f'"{keywords[0]}"'
    return ", ".join(f'"{k}"' for k in keywords[:-1]) + f' and "{keywords[-1]}"'


def _crop_white_borders(image_bytes: bytes, whiteness_threshold: int = 242) -> bytes:
    """Supprime les marges blanches laissées par gpt-image-2 sur les bords.

    Détecte les lignes/colonnes où TOUS les pixels ont une luminance >= threshold
    (proche du blanc pur) et les crop. Le fond crème #F5F0E8 a une luminance
    ~242, donc on met le seuil à 242 : on crop uniquement les vrais bords blancs.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    pixels = img.load()

    def _is_white_row(y: int) -> bool:
        return all(min(pixels[x, y]) >= whiteness_threshold for x in range(w))

    def _is_white_col(x: int) -> bool:
        return all(min(pixels[x, y]) >= whiteness_threshold for y in range(h))

    top = 0
    while top < h and _is_white_row(top):
        top += 1
    bottom = h
    while bottom > top and _is_white_row(bottom - 1):
        bottom -= 1
    left = 0
    while left < w and _is_white_col(left):
        left += 1
    right = w
    while right > left and _is_white_col(right - 1):
        right -= 1

    if (top, left, bottom, right) == (0, 0, h, w):
        logger.info("  Pas de marge blanche détectée, image conservée telle quelle")
        return image_bytes

    cropped = img.crop((left, top, right, bottom))
    logger.info(
        f"  Crop marges blanches : {w}x{h} -> {cropped.size[0]}x{cropped.size[1]} "
        f"(supprimé top={top} bottom={h-bottom} left={left} right={w-right})"
    )
    buf = io.BytesIO()
    cropped.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _format_blocs(blocs: list[dict[str, Any]]) -> str:
    output = []
    for b in blocs:
        points = "\n".join(f'    - "{p}"' for p in b.get("points", []))
        exemple = ""
        if b.get("exemple"):
            exemple = f'\n  Bottom callout reads: "EXEMPLE : {b["exemple"]}"'
        output.append(
            f'Block {b.get("numero", "??")} header title reads exactly: "{b.get("titre", "").upper()}".\n'
            f'  Bullet points read exactly:\n{points}'
            f'{exemple}'
        )
    return "\n\n".join(output)
