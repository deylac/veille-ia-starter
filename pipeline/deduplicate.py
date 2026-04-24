"""Déduplication des news : par URL exacte, puis par similarité de titre."""
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import List

from supabase import create_client

from config.models import NewsItem
from config.settings import SEEN_URLS_FILE

logger = logging.getLogger(__name__)

# Conserver les URLs vues pendant 7 jours pour éviter les republications
URL_CACHE_DAYS = 7

# Nom du fichier cache dans le bucket Supabase (persistance inter-runs sur Railway)
SEEN_URLS_STORAGE_NAME = "seen_urls.json"


def deduplicate(items: List[NewsItem]) -> List[NewsItem]:
    """Supprime les doublons.

    Stratégie en 3 étapes :
    1. URLs déjà traitées les jours précédents (cache disque)
    2. URLs en double dans le batch courant
    3. Titres très similaires (>85% de similarité) entre sources différentes
    """
    seen_urls = _load_seen_urls()
    cutoff = datetime.now(timezone.utc) - timedelta(days=URL_CACHE_DAYS)

    # Nettoyer le cache des vieilles URLs
    seen_urls = {url: ts for url, ts in seen_urls.items() if datetime.fromisoformat(ts) > cutoff}

    # Étape 1 + 2 : filtre par URL
    fresh: List[NewsItem] = []
    seen_in_batch = set()
    for item in items:
        url_hash = _hash_url(item.url)
        if url_hash in seen_urls:
            logger.debug(f"Skip (déjà vu) : {item.title[:60]}")
            continue
        if url_hash in seen_in_batch:
            continue
        seen_in_batch.add(url_hash)
        fresh.append(item)

    # Étape 3 : déduplication par similarité de titre
    deduplicated: List[NewsItem] = []
    for item in fresh:
        is_duplicate = False
        for kept in deduplicated:
            if _similar(item.title, kept.title) > 0.85:
                # On garde celui avec la source la plus officielle (priorité aux RSS officiels)
                if _source_priority(item.source) > _source_priority(kept.source):
                    deduplicated.remove(kept)
                    deduplicated.append(item)
                is_duplicate = True
                break
        if not is_duplicate:
            deduplicated.append(item)

    logger.info(f"Déduplication : {len(items)} -> {len(deduplicated)}")
    return deduplicated


def mark_as_seen(items: List[NewsItem]) -> None:
    """Marque les URLs comme vues pour les prochaines exécutions.

    Sauvegarde localement (debug/dev) ET sur Supabase (persistance Railway).
    """
    seen_urls = _load_seen_urls()
    now_iso = datetime.now(timezone.utc).isoformat()
    for item in items:
        seen_urls[_hash_url(item.url)] = now_iso

    _save_seen_urls(seen_urls)


def _supabase_client():
    """Retourne un client Supabase ou None si non configuré."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.warning(f"Init Supabase échouée pour le cache : {e}")
        return None


def _load_seen_urls() -> dict:
    """Charge le cache depuis Supabase (prioritaire) ou fichier local (fallback)."""
    sb = _supabase_client()
    if sb:
        bucket = os.getenv("SUPABASE_BUCKET", "veille-ia-images")
        try:
            data = sb.storage.from_(bucket).download(SEEN_URLS_STORAGE_NAME)
            content = json.loads(data.decode("utf-8"))
            logger.info(f"Cache seen_urls chargé depuis Supabase ({len(content)} entrées)")
            return content
        except Exception as e:
            logger.info(f"Cache Supabase indisponible ({e}), fallback local")

    if not SEEN_URLS_FILE.exists():
        return {}
    try:
        with open(SEEN_URLS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_seen_urls(seen: dict) -> None:
    """Sauvegarde le cache localement ET sur Supabase si configuré."""
    SEEN_URLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEEN_URLS_FILE, "w") as f:
        json.dump(seen, f)

    sb = _supabase_client()
    if sb:
        bucket = os.getenv("SUPABASE_BUCKET", "veille-ia-images")
        try:
            sb.storage.from_(bucket).upload(
                path=SEEN_URLS_STORAGE_NAME,
                file=json.dumps(seen).encode("utf-8"),
                file_options={"content-type": "application/json", "upsert": "true"},
            )
            logger.info(f"Cache seen_urls uploadé sur Supabase ({len(seen)} entrées)")
        except Exception as e:
            logger.warning(f"Upload Supabase du cache échoué : {e}")


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _source_priority(source: str) -> int:
    """Plus le score est élevé, plus la source est prioritaire en cas de doublon."""
    if any(s in source for s in ("Anthropic", "OpenAI", "Google", "DeepMind", "Mistral")):
        return 3
    if "Newsletter" in source:
        return 2
    if "Reddit" in source:
        return 1
    return 0
