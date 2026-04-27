"""Génération d'images via Gemini 3 Pro Image (Google AI Studio).

Doc API : https://ai.google.dev/gemini-api/docs/image-generation
"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List

from google import genai
from google.genai import types

from config.models import NewsItem
from config.settings import DATA_DIR, GEMINI_API_KEY, GEMINI_IMAGE_MODEL
from observability.api_logger import log_api_call

logger = logging.getLogger(__name__)

IMAGES_DIR = DATA_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)


def generate_images(items: List[NewsItem]) -> List[NewsItem]:
    """Génère une image par news avec Gemini 3 Pro Image."""
    if not items:
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)
    today = datetime.now().strftime("%Y%m%d")

    for i, item in enumerate(items):
        t0 = time.perf_counter()
        try:
            logger.info(f"Génération image {i+1}/{len(items)} (format: {item.visual_format})")

            response = client.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=item.image_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            log_api_call(
                provider="google",
                model=GEMINI_IMAGE_MODEL,
                operation="generate_content",
                duration_ms=int((time.perf_counter() - t0) * 1000),
                success=True,
                context={"step": "image_generation_fallback", "news_title": item.title[:60]},
            )

            # Extraire l'image de la réponse
            image_saved = False
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    filename = f"{today}_{i+1:02d}_{item.visual_format}.png"
                    image_path = IMAGES_DIR / filename
                    with open(image_path, "wb") as f:
                        f.write(part.inline_data.data)
                    item.image_path = str(image_path)
                    image_saved = True
                    logger.info(f"Image sauvegardée : {image_path}")
                    break

            if not image_saved:
                logger.warning(f"Pas d'image générée pour : {item.title[:60]}")

        except Exception as e:
            log_api_call(
                provider="google",
                model=GEMINI_IMAGE_MODEL,
                operation="generate_content",
                duration_ms=int((time.perf_counter() - t0) * 1000),
                success=False,
                error=str(e),
                context={"step": "image_generation_fallback", "news_title": item.title[:60]},
            )
            logger.error(f"Erreur génération image : {e}")

    return [item for item in items if item.image_path]
