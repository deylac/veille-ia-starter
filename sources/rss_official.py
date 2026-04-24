"""Scan des flux RSS officiels (Anthropic, OpenAI, Google, DeepMind, etc.)."""
import logging
from datetime import datetime, timedelta, timezone
from typing import List

import feedparser

from config.models import NewsItem
from config.settings import LOOKBACK_HOURS, RSS_FEEDS

logger = logging.getLogger(__name__)


def fetch_rss_news() -> List[NewsItem]:
    """Récupère les articles publiés dans les dernières LOOKBACK_HOURS heures."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items: List[NewsItem] = []

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            logger.info(f"Scan RSS : {source_name}")
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                published = _parse_date(entry)
                if published and published < cutoff:
                    continue

                summary = entry.get("summary", "") or entry.get("description", "")
                # Nettoyer les balises HTML basiques
                summary = _strip_html(summary)[:1000]

                items.append(
                    NewsItem(
                        title=entry.get("title", "").strip(),
                        url=entry.get("link", ""),
                        source=source_name,
                        summary=summary,
                        published_at=published,
                    )
                )
        except Exception as e:
            logger.warning(f"Erreur RSS {source_name} : {e}")

    logger.info(f"RSS : {len(items)} articles récents collectés")
    return items


def _parse_date(entry) -> datetime | None:
    """Parse la date de publication d'une entrée RSS."""
    for field in ("published_parsed", "updated_parsed"):
        if hasattr(entry, field) and getattr(entry, field):
            try:
                return datetime(*getattr(entry, field)[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _strip_html(text: str) -> str:
    """Strip basique des balises HTML."""
    import re

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
