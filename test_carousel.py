"""Test isolé de la phase 7 (carrousel Instagram Gemini).

Workflow :
1. Collecte + dedup + scoring (rapide, ~1 min, ~0,05 €)
2. SKIP phases 4-5-6 (enrichissement + infographies OpenAI + push infographies)
3. Construction du carrousel (pur local, gratuit)
4. Génération des N+2 slides via Gemini (rapide, ~3 min, ~0,40 €)
5. Push d'une seule page "Carrousel" dans Notion

Coût total : ~0,50 €, durée ~5-6 min.

Usage : python test_carousel.py
"""
import logging
import sys

from generation.gemini_carousel import generate_carousel_images
from pipeline.carousel_builder import build_carousel
from pipeline.deduplicate import deduplicate
from pipeline.score_viral import score_news
from publish.notion_push import push_carousel_to_notion
from sources.newsletters import fetch_newsletter_news
from sources.rss_official import fetch_rss_news


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    setup_logging()
    logging.info("=== TEST CARROUSEL (phase 7 isolée) ===")

    # 1. Collecte
    items = []
    items.extend(fetch_rss_news())
    items.extend(fetch_newsletter_news())
    logging.info(f"Collecte : {len(items)} news brutes")
    if not items:
        logging.warning("Aucune news, stop.")
        return

    # 2. Dédup + scoring (rapide, on a besoin des scores pour classer les slides)
    items = deduplicate(items)
    items = score_news(items)
    if not items:
        logging.warning("Aucune news n'a passé le seuil.")
        return

    logging.info(f"Top {len(items)} news qualifiées")

    # 3. Construction + génération du carrousel
    carousel = build_carousel(items)
    if not carousel:
        logging.warning("Carrousel vide.")
        return

    slide_paths = generate_carousel_images(carousel)
    if not slide_paths:
        logging.error("Aucune slide générée.")
        return

    # 4. Push Notion
    success = push_carousel_to_notion(slide_paths, carousel)
    logging.info(f"\n=== RÉSULTAT : {len(slide_paths)} slides générées, Notion push = {success} ===")
    for p in slide_paths:
        logging.info(f"  {p}")


if __name__ == "__main__":
    main()
