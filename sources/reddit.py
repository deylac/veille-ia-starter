"""Scan des subreddits IA pertinents."""
import logging
from datetime import datetime, timedelta, timezone
from typing import List

import praw

from config.models import NewsItem
from config.settings import (
    LOOKBACK_HOURS,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    SUBREDDITS,
    SUBREDDIT_MIN_UPVOTES,
)

logger = logging.getLogger(__name__)


def fetch_reddit_news() -> List[NewsItem]:
    """Récupère les top posts récents des subreddits IA."""
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        logger.warning("Reddit non configuré (clés manquantes), skip")
        return []

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    reddit.read_only = True

    cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).timestamp()
    items: List[NewsItem] = []

    for sub in SUBREDDITS:
        try:
            logger.info(f"Scan Reddit : r/{sub}")
            # On prend le top des dernières 24h (filtre 'day') pour avoir les meilleures
            for post in reddit.subreddit(sub).top(time_filter="day", limit=15):
                if post.created_utc < cutoff_ts:
                    continue
                if post.score < SUBREDDIT_MIN_UPVOTES:
                    continue
                if post.stickied:
                    continue

                # Ignorer les posts purement images/memes
                if post.is_self:
                    summary = (post.selftext or "")[:1000]
                else:
                    summary = post.url[:500]

                items.append(
                    NewsItem(
                        title=post.title.strip(),
                        url=f"https://www.reddit.com{post.permalink}",
                        source=f"Reddit r/{sub}",
                        summary=summary,
                        published_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                        raw_score=post.score,
                    )
                )
        except Exception as e:
            logger.warning(f"Erreur Reddit r/{sub} : {e}")

    logger.info(f"Reddit : {len(items)} posts collectés")
    return items
