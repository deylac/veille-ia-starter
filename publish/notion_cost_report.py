"""Page Notion 'Coûts API' — créée 1 fois, mise à jour à chaque run.

Workflow :
- Setup (1 fois en local) : `python setup_cost_report_page.py` crée une sous-page
  enfant de NOTION_PARENT_PAGE_ID et affiche son ID à mettre dans .env comme
  NOTION_COST_REPORT_PAGE_ID.
- Run quotidien : `update_cost_report_page()` est appelé à la fin de main.py.
  Il vide les blocs existants et republie un récap frais.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from notion_client import Client

from config.settings import NOTION_API_KEY, TZ
from observability.api_logger import fetch_recent_calls

logger = logging.getLogger(__name__)


def create_cost_report_page(parent_page_id: str) -> str:
    """Crée la sous-page une fois. Retourne son ID. À appeler depuis le script setup."""
    notion = Client(auth=NOTION_API_KEY)
    response = notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={
            "title": {
                "title": [{"text": {"content": "💰 Coûts API — Veille IA"}}]
            }
        },
    )
    page_id = response["id"]
    logger.info(f"Sous-page Notion créée : {page_id}")
    return page_id


def update_cost_report_page(page_id: str) -> bool:
    """Vide la page et republie un récap à jour. Best-effort, ne crashe pas le pipeline."""
    if not page_id:
        return False
    try:
        notion = Client(auth=NOTION_API_KEY)
        rows = fetch_recent_calls(days=30)
        blocks = _build_report_blocks(rows)

        _clear_page_blocks(notion, page_id)
        # Notion limite à 100 enfants par requête : on chunk si besoin
        for chunk_start in range(0, len(blocks), 100):
            chunk = blocks[chunk_start : chunk_start + 100]
            notion.blocks.children.append(block_id=page_id, children=chunk)
        logger.info(f"Page Notion coûts API mise à jour ({len(blocks)} blocs)")
        return True
    except Exception as e:
        logger.error(f"Echec mise à jour page coûts Notion : {type(e).__name__} : {e}")
        return False


def _clear_page_blocks(notion: Client, page_id: str) -> None:
    """Supprime tous les blocs enfants de la page (avant repush)."""
    children = notion.blocks.children.list(block_id=page_id, page_size=100)
    for block in children.get("results", []):
        try:
            notion.blocks.delete(block_id=block["id"])
        except Exception as e:
            logger.debug(f"Suppression bloc {block['id']} échouée : {e}")


def _build_report_blocks(rows: list[dict[str, Any]]) -> list[dict]:
    """Construit la liste de blocs Notion à partir des lignes api_calls."""
    today = datetime.now(TZ).date()
    today_iso = today.isoformat()
    cutoff_7 = (today - timedelta(days=6)).isoformat()
    cutoff_30 = (today - timedelta(days=29)).isoformat()

    today_rows = [r for r in rows if r.get("date", "") == today_iso]
    last_7_rows = [r for r in rows if r.get("date", "") >= cutoff_7]
    last_30_rows = [r for r in rows if r.get("date", "") >= cutoff_30]

    today_cost = sum(float(r.get("cost_estimate_usd") or 0) for r in today_rows)
    today_calls = len(today_rows)
    cost_7 = sum(float(r.get("cost_estimate_usd") or 0) for r in last_7_rows)
    cost_30 = sum(float(r.get("cost_estimate_usd") or 0) for r in last_30_rows)
    daily_avg_30 = cost_30 / max(1, len(set(r.get("date", "") for r in last_30_rows)))
    monthly_projection = daily_avg_30 * 30

    # Détail aujourd'hui par modèle
    by_model_today: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "cost": 0.0, "provider": ""}
    )
    for r in today_rows:
        m = r.get("model", "")
        by_model_today[m]["calls"] += 1
        by_model_today[m]["cost"] += float(r.get("cost_estimate_usd") or 0)
        by_model_today[m]["provider"] = r.get("provider", "")

    # Détail aujourd'hui par étape
    by_step_today: dict[str, dict[str, Any]] = defaultdict(lambda: {"calls": 0, "cost": 0.0})
    for r in today_rows:
        ctx = r.get("context") or {}
        step = ctx.get("step", "(unknown)") if isinstance(ctx, dict) else "(unknown)"
        by_step_today[step]["calls"] += 1
        by_step_today[step]["cost"] += float(r.get("cost_estimate_usd") or 0)

    blocks: list[dict] = []
    blocks.append(_callout(
        f"📅 Mis à jour le {datetime.now(TZ).strftime('%Y-%m-%d à %Hh%M')} (Europe/Paris)",
        emoji="🔄",
    ))

    # === Synthèse ===
    blocks.append(_heading_2("Synthèse"))
    blocks.append(_paragraph(""))
    blocks.append(_callout(
        f"💵 Aujourd'hui : ${today_cost:.3f}  ({today_calls} appels API)",
        emoji="📅",
        color="blue_background",
    ))
    blocks.append(_callout(
        f"💵 7 derniers jours : ${cost_7:.2f}  ({len(last_7_rows)} appels)",
        emoji="📊",
        color="default",
    ))
    blocks.append(_callout(
        f"💵 30 derniers jours : ${cost_30:.2f}  ({len(last_30_rows)} appels)",
        emoji="📈",
        color="default",
    ))
    blocks.append(_callout(
        f"🔮 Projection mensuelle : ${monthly_projection:.2f}  "
        f"(moyenne ${daily_avg_30:.3f} / jour sur les 30 derniers jours)",
        emoji="🎯",
        color="purple_background",
    ))

    # === Détail aujourd'hui par modèle ===
    blocks.append(_heading_2("Détail aujourd'hui — par modèle"))
    if by_model_today:
        for model, a in sorted(by_model_today.items(), key=lambda kv: -kv[1]["cost"]):
            blocks.append(_bullet(
                f"{a['provider']} / {model} — {a['calls']} appel(s) — ${a['cost']:.3f}"
            ))
    else:
        blocks.append(_paragraph("Aucun appel aujourd'hui (le pipeline n'a pas tourné)."))

    # === Détail aujourd'hui par étape ===
    blocks.append(_heading_2("Détail aujourd'hui — par étape du pipeline"))
    if by_step_today:
        for step, a in sorted(by_step_today.items(), key=lambda kv: -kv[1]["cost"]):
            blocks.append(_bullet(f"{step} — {a['calls']} appel(s) — ${a['cost']:.3f}"))
    else:
        blocks.append(_paragraph("—"))

    # === Footer ===
    blocks.append(_divider())
    blocks.append(_paragraph(
        "Source : table Supabase `api_calls` alimentée par observability/api_logger.py. "
        "Pour le détail brut : `python report_api_usage.py --days 30 --by model`"
    ))

    return blocks


# === Helpers blocs Notion ===

def _heading_2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _callout(text: str, emoji: str = "💡", color: str = "default") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": emoji},
            "color": color,
        },
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}
