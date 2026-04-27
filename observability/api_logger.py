"""Logger structuré pour les appels API LLM (Anthropic, OpenAI, Google).

Chaque appel API du pipeline (scoring, enrichissement, génération image, etc.)
est journalisé via `log_api_call(...)`. Le log est inscrit dans Supabase si la
configuration est présente, sinon dans un fichier JSONL local.

Ne JAMAIS faire crasher le pipeline si le log échoue : le logging est best-effort.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config.settings import DATA_DIR, TZ

logger = logging.getLogger(__name__)

LOCAL_LOG_FILE = DATA_DIR / "api_calls.jsonl"

# Tarifs en USD. Source de vérité = pages pricing officielles.
# Date de dernière vérification : 2026-04-27.
#
# CONFIRMÉ (Brice 2026-04-27, source : platform.claude.com/docs/en/about-claude/pricing) :
#   - Claude Sonnet 4.6 : input $3/MTok, output $15/MTok, cache hit $0.30/MTok
#   - Web search : $10 / 1 000 recherches = $0.01 / search
#
# À CONFIRMER :
#   - gpt-image-2 (modèle "gpt-image-2-2026-04-21" dans config/settings.py) : la page
#     pricing OpenAI renvoie vers un calculator dynamique. Tarif provisoire $0.167/img
#     (équivalent gpt-image-1 high quality 1024x1536). À remplacer dès que Brice
#     fournit la page officielle ou un coût réel observé sur 1 facture.
#   - Gemini 3 Pro Image : aucune source officielle reçue. Tarif provisoire $0.04/img
#     (équivalent Imagen 3 Standard de mémoire). À remplacer.
PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input": 3.0 / 1_000_000,             # CONFIRMÉ
        "output": 15.0 / 1_000_000,           # CONFIRMÉ
        "cache_read_input": 0.30 / 1_000_000, # CONFIRMÉ — pas encore utilisé (pas de prompt caching dans le pipeline)
    },
    "gpt-image-2-2026-04-21": {
        "per_image": 0.040,           # CALÉ sur facture réelle Brice 26-04-2026 ($0.17 / ~4 images)
    },
    "gemini-3-pro-image-preview": {
        "per_image": 0.04,            # ⚠️ À CONFIRMER (estimation par parité Imagen)
    },
    "web_search_20250305": {
        "per_use": 0.01,              # CONFIRMÉ ($10 / 1k recherches)
    },
}


def _supabase_client():
    """Initialise un client Supabase si les vars d'env sont présentes, sinon None."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        logger.debug(f"api_logger: init Supabase échouée ({e}), fallback local")
        return None


def _estimate_cost(
    model: str,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    operation: str,
) -> float:
    """Calcule un coût USD estimé selon le modèle et l'usage."""
    pricing = PRICING.get(model)
    if not pricing:
        return 0.0

    # Modèles texte facturés au token
    if "input" in pricing and "output" in pricing:
        cost = 0.0
        if input_tokens:
            cost += input_tokens * pricing["input"]
        if output_tokens:
            cost += output_tokens * pricing["output"]
        return round(cost, 6)

    # Modèles image facturés à l'unité
    if "per_image" in pricing:
        return round(pricing["per_image"], 6)

    # Tools (web search) facturés à l'usage
    if "per_use" in pricing:
        return round(pricing["per_use"], 6)

    return 0.0


def log_api_call(
    provider: str,
    model: str,
    operation: str,
    duration_ms: int,
    success: bool,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    error: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> None:
    """Enregistre un appel API. Tout est best-effort, n'élève jamais d'exception.

    Args:
        provider: 'anthropic' | 'openai' | 'google'
        model: ID exact du modèle (ex: 'claude-sonnet-4-6', 'gpt-image-2-2026-04-21')
        operation: 'messages.create' | 'images.generate' | 'generate_content' | ...
        duration_ms: durée totale de l'appel (mesure côté client)
        success: True si l'appel a abouti, False sinon
        input_tokens / output_tokens: usage tokens si disponible (texte)
        error: message d'erreur si success=False
        context: dict additionnel libre, sera stocké en jsonb
    """
    try:
        now = datetime.now(TZ)
        row = {
            "timestamp": now.isoformat(),
            "date": now.date().isoformat(),
            "provider": provider,
            "model": model,
            "operation": operation,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "success": success,
            "error": (error or "")[:500] if error else None,
            "cost_estimate_usd": _estimate_cost(model, input_tokens, output_tokens, operation),
            "context": context or {},
        }

        sb = _supabase_client()
        if sb:
            try:
                sb.table("api_calls").insert(row).execute()
                return
            except Exception as e:
                logger.debug(f"api_logger: insert Supabase échouée ({e}), fallback local")

        # Fallback : append JSONL local
        LOCAL_LOG_FILE.parent.mkdir(exist_ok=True)
        with open(LOCAL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        # Best-effort : on log un debug et on ne crashe jamais
        logger.debug(f"api_logger: log_api_call a échoué silencieusement ({e})")


def fetch_recent_calls(days: int = 7) -> list[dict[str, Any]]:
    """Récupère les appels API des N derniers jours, depuis Supabase ou JSONL local.

    Utilisé par report_api_usage.py.
    """
    sb = _supabase_client()
    if sb:
        try:
            from datetime import timedelta
            cutoff = (datetime.now(TZ).date() - timedelta(days=days - 1)).isoformat()
            res = sb.table("api_calls").select("*").gte("date", cutoff).order("timestamp", desc=False).execute()
            return res.data or []
        except Exception as e:
            logger.warning(f"Lecture Supabase échouée ({e}), fallback fichier local")

    # Fallback fichier local
    if not LOCAL_LOG_FILE.exists():
        return []
    rows: list[dict[str, Any]] = []
    from datetime import timedelta
    cutoff_date = (datetime.now(TZ).date() - timedelta(days=days - 1)).isoformat()
    with open(LOCAL_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if row.get("date", "") >= cutoff_date:
                    rows.append(row)
            except json.JSONDecodeError:
                continue
    return rows
