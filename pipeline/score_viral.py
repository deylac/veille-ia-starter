"""Scoring du potentiel viral de chaque news par Claude.

On envoie toutes les news en un seul appel pour avoir une cohérence relative
entre les scores (Claude voit toutes les options et peut comparer).
"""
import json
import logging
import time
from typing import List

from anthropic import Anthropic

from config.models import NewsItem
from config.settings import (
    ANTHROPIC_API_KEY,
    AUDIENCE_DESCRIPTION,
    CLAUDE_MODEL,
    MAX_NEWS_PER_DAY,
    MIN_VIRAL_SCORE,
    TOPIC_DESCRIPTION,
    TOPIC_NAME,
)
from observability.api_logger import log_api_call
from pipeline.run_report import RunReport

logger = logging.getLogger(__name__)


def score_news(items: List[NewsItem], report: RunReport | None = None) -> List[NewsItem]:
    """Score chaque news de 1 à 10 sur son potentiel viral.

    Renvoie uniquement les news ayant atteint MIN_VIRAL_SCORE,
    triées par score décroissant et plafonnées à MAX_NEWS_PER_DAY.

    Si `report` est fourni, y pousse la liste complète des scores avec leurs raisons
    (retenus ET rejetés), pour le rapport quotidien Notion.
    """
    if not items:
        return []

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Préparer les news pour le prompt
    news_blocks = []
    for i, item in enumerate(items):
        block = f"[{i}] SOURCE: {item.source}\nTITRE: {item.title}\nRESUME: {item.summary[:500]}\n"
        news_blocks.append(block)

    news_text = "\n---\n".join(news_blocks)

    prompt = f"""Tu es un expert en stratégie de contenu sur le sujet : {TOPIC_DESCRIPTION}, pour audience francophone.

{AUDIENCE_DESCRIPTION}

Voici les news collectées dans les dernières 24h sur le sujet "{TOPIC_NAME}". Pour chacune, tu dois :
1. Donner un score de potentiel viral de 1 à 10 (10 = explosif pour notre audience)
2. Suggérer un angle éditorial percutant en français (1 phrase)
3. Proposer un hook LinkedIn en français (1-2 lignes max, accrocheur)

NEWS À ÉVALUER :

{news_text}

Réponds UNIQUEMENT avec un JSON valide de cette forme (pas de markdown, pas de prose) :
{{
  "scores": [
    {{
      "index": 0,
      "score": 8,
      "reason": "Annonce produit majeure qui change le quotidien",
      "angle": "Anthropic vient de rendre votre journée 30% plus productive sans que vous le sachiez",
      "hook": "Anthropic a sorti une fonctionnalité hier soir.\\n\\nElle va changer votre façon de bosser avec Claude."
    }},
    ...
  ]
}}

Règles importantes pour les scores :
- 9-10 : annonce produit majeure ou stat qui va casser internet
- 7-8 : news intéressante qui mérite un post
- 5-6 : intéressant mais sans plus
- 1-4 : pas pour notre audience (trop technique, niche, ou peu d'impact)

Pour les hooks : pas d'emoji, pas de tirets cadratins (utilise un point ou une virgule), ton direct et concret."""

    t0 = time.perf_counter()
    try:
        logger.info(f"Scoring de {len(items)} news par Claude...")
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        log_api_call(
            provider="anthropic",
            model=CLAUDE_MODEL,
            operation="messages.create",
            duration_ms=int((time.perf_counter() - t0) * 1000),
            success=True,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
            context={"step": "scoring", "n_news": len(items)},
        )
        text = response.content[0].text.strip()

        # Nettoyer un éventuel markdown
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        data = json.loads(text)
        scores = {s["index"]: s for s in data["scores"]}

        # Appliquer les scores
        for i, item in enumerate(items):
            score_data = scores.get(i)
            if score_data:
                item.viral_score = score_data["score"]
                item.viral_reason = score_data.get("reason", "")
                item.editorial_angle = score_data.get("angle", "")
                item.hook_fr = score_data.get("hook", "")
            else:
                item.viral_score = 0

    except Exception as e:
        log_api_call(
            provider="anthropic",
            model=CLAUDE_MODEL,
            operation="messages.create",
            duration_ms=int((time.perf_counter() - t0) * 1000),
            success=False,
            error=str(e),
            context={"step": "scoring", "n_news": len(items)},
        )
        logger.error(f"Erreur scoring Claude : {e}")
        return []

    # Filtrer et trier
    qualified = [item for item in items if (item.viral_score or 0) >= MIN_VIRAL_SCORE]
    qualified.sort(key=lambda x: x.viral_score or 0, reverse=True)
    selected = qualified[:MAX_NEWS_PER_DAY]

    # Pousser le détail au RunReport (toutes les news scorées, retenues ou non)
    if report is not None:
        kept_urls = {it.url for it in selected}
        report.set_scoring([
            {
                "title": it.title[:200],
                "source": it.source,
                "score": it.viral_score or 0,
                "reason": it.viral_reason[:300],
                "kept": it.url in kept_urls,
            }
            for it in sorted(items, key=lambda x: x.viral_score or 0, reverse=True)
        ])

    logger.info(
        f"Scoring : {len(qualified)} news ont atteint le seuil de {MIN_VIRAL_SCORE}, "
        f"on garde le top {len(selected)}"
    )
    return selected
