"""Point d'entrée du pipeline de veille IA.

Lancé par le cron Railway tous les jours à 7h00 (Europe/Madrid).
Peut aussi être lancé manuellement : python main.py
"""
import logging
import sys
from datetime import datetime

from config.settings import TZ
from generation.gemini_carousel import generate_carousel_images
from generation.openai_image import generate_images
from pipeline.carousel_builder import build_carousel
from pipeline.content_enrichment import enrich_news_content
from pipeline.deduplicate import deduplicate, mark_as_seen
from pipeline.score_viral import score_news
from publish.notion_push import push_carousel_to_notion, push_to_notion
from sources.newsletters import fetch_newsletter_news
from sources.reddit import fetch_reddit_news
from sources.rss_official import fetch_rss_news


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run() -> int:
    """Lance le pipeline complet. Retourne le nombre d'images créées en Notion."""
    start = datetime.now(TZ)
    logging.info(f"=== Démarrage veille IA : {start.strftime('%Y-%m-%d %H:%M:%S %Z')} ===")

    # 1. Collecte multi-sources
    logging.info("--- Phase 1 : collecte multi-sources ---")
    items = []
    items.extend(fetch_rss_news())
    items.extend(fetch_reddit_news())
    items.extend(fetch_newsletter_news())
    logging.info(f"Total brut collecté : {len(items)} news")

    if not items:
        logging.warning("Aucune news collectée, arrêt du pipeline")
        return 0

    # 2. Déduplication
    logging.info("--- Phase 2 : déduplication ---")
    items = deduplicate(items)

    if not items:
        logging.info("Toutes les news sont déjà connues, arrêt")
        return 0

    # 3. Scoring viral (filtre + tri + plafond)
    logging.info("--- Phase 3 : scoring viral ---")
    items = score_news(items)

    if not items:
        logging.info("Aucune news n'a passé le seuil viral")
        # On marque quand même comme vues pour ne pas les rescorer demain
        # (tu peux commenter cette ligne si tu préfères les revoir si elles deviennent populaires)
        return 0

    # 4. Enrichissement contenu (web search Claude + JSON structuré pour infographie)
    logging.info("--- Phase 4 : enrichissement contenu (web search) ---")
    items = enrich_news_content(items)

    # 5. Génération des images (OpenAI gpt-image-2, format infographie magazine cyan)
    logging.info("--- Phase 5 : génération des infographies ---")
    items = generate_images(items)

    if not items:
        logging.warning("Aucune image n'a pu être générée")
        return 0

    # 6. Publication des infographies dans Notion
    logging.info("--- Phase 6 : publication infographies Notion ---")
    created = push_to_notion(items)

    # 7. Carrousel Instagram (Gemini, format 1080x1350)
    logging.info("--- Phase 7 : carrousel Instagram (Gemini) ---")
    try:
        carousel = build_carousel(items)
        if carousel:
            slide_paths = generate_carousel_images(carousel)
            if slide_paths:
                push_carousel_to_notion(slide_paths, carousel)
    except Exception as e:
        logging.exception(f"Carrousel échoué (non bloquant) : {e}")

    # 8. Marquer les URLs comme vues pour éviter les doublons
    mark_as_seen(items)

    duration = (datetime.now(TZ) - start).total_seconds()
    logging.info(f"=== Terminé : {created} infographies + 1 carrousel poussés en {duration:.1f}s ===")
    return created


if __name__ == "__main__":
    setup_logging()
    try:
        run()
    except Exception as e:
        logging.exception(f"Erreur fatale : {e}")
        sys.exit(1)
