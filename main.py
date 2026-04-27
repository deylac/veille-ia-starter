"""Point d'entrée du pipeline de veille IA.

Lancé par le cron Railway tous les jours à 7h00 (Europe/Madrid).
Peut aussi être lancé manuellement : python main.py
"""
import logging
import sys
from datetime import datetime

from config.settings import NOTION_COST_REPORT_PAGE_ID, NOTION_DAILY_REPORT_PAGE_ID, TZ
from generation.gemini_carousel import generate_carousel_images
from generation.openai_image import generate_images
from pipeline.carousel_builder import build_carousel
from pipeline.content_enrichment import enrich_news_content
from pipeline.deduplicate import deduplicate, mark_as_seen
from pipeline.editorial_director import direct_editorial
from pipeline.run_report import RunReport
from pipeline.score_viral import score_news
from publish.notion_cost_report import update_cost_report_page
from publish.notion_daily_report import update_daily_report_page
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


def _publish_reports(report: RunReport) -> None:
    """Publie le rapport quotidien (toujours) + le rapport coûts API.

    Best-effort : ne lève jamais. Appelé même si le pipeline a fait early-exit.
    """
    if NOTION_DAILY_REPORT_PAGE_ID:
        try:
            update_daily_report_page(NOTION_DAILY_REPORT_PAGE_ID, report)
        except Exception as e:
            logging.exception(f"Push rapport quotidien échoué : {e}")
    if NOTION_COST_REPORT_PAGE_ID:
        try:
            update_cost_report_page(NOTION_COST_REPORT_PAGE_ID)
        except Exception as e:
            logging.exception(f"Push rapport coûts échoué : {e}")


def run() -> int:
    """Lance le pipeline complet. Retourne le nombre d'images créées en Notion."""
    start = datetime.now(TZ)
    logging.info(f"=== Démarrage veille IA : {start.strftime('%Y-%m-%d %H:%M:%S %Z')} ===")

    # Collecteur d'événements pour le rapport quotidien Notion
    report = RunReport(start_time=start)

    # 1. Collecte multi-sources
    logging.info("--- Phase 1 : collecte multi-sources ---")
    rss_items = fetch_rss_news()
    reddit_items = fetch_reddit_news()
    newsletter_items = fetch_newsletter_news()
    report.add_collected("RSS officiels", len(rss_items))
    report.add_collected("Reddit", len(reddit_items))
    report.add_collected("Newsletters Gmail", len(newsletter_items))
    items = rss_items + reddit_items + newsletter_items
    logging.info(f"Total brut collecté : {len(items)} news")

    if not items:
        logging.warning("Aucune news collectée, arrêt du pipeline")
        report.set_early_exit("Aucune news collectée")
        _publish_reports(report)
        return 0

    # 2. Déduplication
    logging.info("--- Phase 2 : déduplication ---")
    items = deduplicate(items)

    if not items:
        logging.info("Toutes les news sont déjà connues, arrêt")
        report.set_early_exit("Toutes les news étaient déjà vues (déduplication 100%)")
        _publish_reports(report)
        return 0

    # 3. Scoring viral (filtre + tri + plafond)
    logging.info("--- Phase 3 : scoring viral ---")
    items = score_news(items, report=report)

    if not items:
        logging.info("Aucune news n'a passé le seuil viral")
        report.set_early_exit("Aucune news n'a atteint le seuil viral 7/10")
        _publish_reports(report)
        return 0

    # 3.5. Direction éditoriale : cluster thématique, merge, angles variés, rejet HS
    logging.info("--- Phase 3.5 : direction éditoriale ---")
    items = direct_editorial(items, report=report)

    if not items:
        logging.warning("Le chef éditorial a tout rejeté, arrêt du pipeline")
        report.set_early_exit("Le chef éditorial a rejeté toutes les news")
        _publish_reports(report)
        return 0

    # 4. Enrichissement contenu (web search Claude + JSON structuré pour infographie)
    logging.info("--- Phase 4 : enrichissement contenu (web search) ---")
    items = enrich_news_content(items)
    report.set_enriched(len(items))

    # 5. Génération des images (OpenAI gpt-image-2, format infographie magazine cyan)
    logging.info("--- Phase 5 : génération des infographies ---")
    items = generate_images(items)

    if not items:
        logging.warning("Aucune image n'a pu être générée")
        report.set_early_exit("Aucune image n'a pu être générée (échec OpenAI)")
        _publish_reports(report)
        return 0

    # 6. Publication des infographies dans Notion
    logging.info("--- Phase 6 : publication infographies Notion ---")
    created = push_to_notion(items)
    report.set_published(created)

    # 7. Carrousel Instagram (Gemini, format 1080x1350)
    logging.info("--- Phase 7 : carrousel Instagram (Gemini) ---")
    try:
        carousel = build_carousel(items)
        if carousel:
            slide_paths = generate_carousel_images(carousel)
            if slide_paths:
                push_carousel_to_notion(slide_paths, carousel)
                report.set_carousel(len(slide_paths))
    except Exception as e:
        logging.exception(f"Carrousel échoué (non bloquant) : {e}")

    # 8. Marquer les URLs comme vues pour éviter les doublons
    mark_as_seen(items)

    # 9. Publier les rapports Notion (quotidien + coûts API)
    _publish_reports(report)

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
