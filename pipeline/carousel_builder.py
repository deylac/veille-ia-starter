"""Construit la structure du carrousel Instagram quotidien.

Réutilise les news déjà scorées (Phase 3) et enrichies (Phase 4) pour produire
la liste de slides à générer par Gemini :
- 1 slide COVER : "Les N actus {TOPIC_NAME} du JJ/MM"
- N slides NEWS : 1 par news, avec numéro "01/N", titre, hook, stat clé
- 1 slide OUTRO : "Sauvegardez et partagez"

Pas d'appel API : pure logique de reformatage des données existantes.
"""
import logging
from datetime import datetime
from typing import Any, List

from config.models import NewsItem
from config.settings import BRAND_NAME, TOPIC_NAME, TZ

logger = logging.getLogger(__name__)


def build_carousel(items: List[NewsItem]) -> dict[str, Any]:
    """Retourne un dict {date, cover, slides, outro} prêt pour la génération Gemini.

    Prend les meilleures news (tri par viral_score décroissant, plafond à 8 pour
    garder le carrousel à 10 slides total).
    """
    if not items:
        return {}

    # Tri par score viral descendant, plafond 8 news (cover + 8 news + outro = 10 slides)
    sorted_items = sorted(items, key=lambda x: x.viral_score or 0, reverse=True)[:8]
    n = len(sorted_items)

    now = datetime.now(TZ)
    date_long_fr = _format_date_fr(now)
    date_short = now.strftime("%d/%m")

    cover = {
        "type": "cover",
        "title_main": f"LES {n} ACTUS {TOPIC_NAME.upper()}",
        "title_sub": f"DU JOUR",
        "date": date_long_fr,  # "23 AVRIL 2026"
        "hook": f"Les news qui vont changer votre {_profession_target()} aujourd'hui.",
    }

    slides: list[dict[str, Any]] = []
    for i, item in enumerate(sorted_items, start=1):
        sc = item.structured_content or {}
        # On privilégie le titre FR issu de l'enrichissement (après chef éditorial
        # + content_enrichment). item.title est la version propre en FR après merge
        # éditorial. sc.get("titre") est la version en MAJUSCULES destinée à
        # l'infographie — pour le carrousel on préfère le titre normal.
        title_fr = item.title or sc.get("titre") or ""
        # Hook : sous-titre FR si dispo, sinon angle éditorial du scoring
        hook_fr = sc.get("sous_titre") or item.editorial_angle or item.hook_fr or ""
        slides.append({
            "type": "news",
            "numero": f"{i:02d}/{n:02d}",
            "title": title_fr[:80],
            "hook": hook_fr[:140],
            "stat": _extract_stat(item),
            "score": item.viral_score or 0,
        })

    outro = {
        "type": "outro",
        "title_main": "SAUVEGARDEZ",
        "title_sub": "ET PARTAGEZ",
        "hook": f"Retrouvez {BRAND_NAME} chaque matin.",
        "date": date_short,
    }

    logger.info(f"Carrousel construit : cover + {n} slides news + outro ({n+2} slides total)")
    return {
        "date": date_long_fr,
        "date_short": date_short,
        "cover": cover,
        "slides": slides,
        "outro": outro,
    }


def _format_date_fr(dt: datetime) -> str:
    """Formate la date en français majuscule (ex: '23 AVRIL 2026')."""
    months_fr = [
        "JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN",
        "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE",
    ]
    return f"{dt.day} {months_fr[dt.month - 1]} {dt.year}"


def _profession_target() -> str:
    """Accroche ciblée pour l'audience."""
    return "quotidien de freelance"


def _extract_stat(item: NewsItem) -> str:
    """Extrait une stat marquante depuis le contenu structuré si disponible, sinon fallback."""
    if item.structured_content and item.structured_content.get("stat"):
        stat = item.structured_content["stat"]
        if stat and stat != "NOUVEAU":
            return stat[:8]
    return ""
