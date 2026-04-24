"""Test rapide du nouveau pipeline (enrichissement + image OpenAI) sur 1-2 news.

Usage : python test_pipeline.py [N]
  - N : nombre de news à tester (défaut 1, max 3)

Ne pousse PAS dans Notion. Sauvegarde l'image localement et logge tout pour debug.
"""
import json
import logging
import sys
from datetime import datetime, timedelta, timezone

from config.models import NewsItem
from config.settings import TZ
from generation.openai_image import generate_images
from pipeline.content_enrichment import enrich_news_content
from pipeline.deduplicate import deduplicate
from pipeline.editorial_director import direct_editorial
from pipeline.score_viral import score_news
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
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n = max(1, min(3, n))
    logging.info(f"=== TEST PIPELINE : {n} news ===")

    # 1. Collecte
    items: list[NewsItem] = []
    items.extend(fetch_rss_news())
    items.extend(fetch_newsletter_news())
    logging.info(f"Collecte : {len(items)} news brutes")

    # 2. Dédup
    items = deduplicate(items)

    # 3. Scoring
    items = score_news(items)
    if not items:
        logging.warning("Aucune news sélectionnée. Stop.")
        return

    # 3.5. Direction éditoriale (cluster + angle + merge)
    items = direct_editorial(items)
    items = items[:n]  # on limite après le chef édito pour voir le merge à l'œuvre
    logging.info(
        f"Sélection top {n} après chef édito : "
        f"{[(it.title[:40], it.editorial_angle_type) for it in items]}"
    )

    if not items:
        logging.warning("Aucune news après chef édito. Stop.")
        return

    # 4. Enrichissement (web search Claude + JSON structuré, respecte l'angle)
    items = enrich_news_content(items)

    # Affichage du JSON structuré
    for it in items:
        logging.info(f"\n--- JSON STRUCTURÉ : {it.title[:60]} ---")
        logging.info(json.dumps(it.structured_content, indent=2, ensure_ascii=False))
        logging.info(f"Sources web utilisées : {it.web_sources}")

    # 5. Génération image
    items = generate_images(items)

    # Récap final
    logging.info("\n=== RÉSULTAT ===")
    for it in items:
        logging.info(f"  - {it.title[:60]}")
        logging.info(f"    Image : {it.image_path}")
        logging.info(f"    Prompt envoyé (longueur) : {len(it.image_prompt)} chars")


if __name__ == "__main__":
    main()
