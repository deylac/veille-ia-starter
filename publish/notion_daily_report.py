"""Page Notion 'Rapport quotidien' — créée 1 fois, mise à jour à chaque run.

Stocke chaque run dans la table Supabase `daily_runs`, puis republie la page
avec : aujourd'hui détaillé en haut, 6 jours précédents en toggles repliables.

Setup (1 fois en local) :
    python setup_daily_report_page.py
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from notion_client import Client

from config.settings import BRAND_NAME, NOTION_API_KEY, TZ
from pipeline.run_report import RunReport

logger = logging.getLogger(__name__)


# === Setup (one-shot) ===

def create_daily_report_page(parent_page_id: str) -> str:
    notion = Client(auth=NOTION_API_KEY)
    response = notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={"title": {"title": [{"text": {"content": f"🗞️ Rapport quotidien — {BRAND_NAME}"}}]}},
    )
    page_id = response["id"]
    logger.info(f"Sous-page rapport quotidien créée : {page_id}")
    return page_id


# === Persistence ===

def _supabase_client():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        logger.debug(f"Init Supabase échouée : {e}")
        return None


def _persist_run(report: RunReport) -> None:
    """Upsert du run du jour dans daily_runs (idempotent : rejeu = écrasement)."""
    sb = _supabase_client()
    if not sb:
        logger.warning("Supabase non configuré, le rapport quotidien ne sera pas persisté")
        return
    try:
        sb.table("daily_runs").upsert(report.to_db_row()).execute()
    except Exception as e:
        logger.error(f"Persistence daily_runs échouée : {type(e).__name__} : {e}")


def _fetch_last_n_runs(n: int = 7) -> list[dict[str, Any]]:
    """Récupère les N derniers runs (ordre chronologique inverse, plus récent en 0)."""
    sb = _supabase_client()
    if not sb:
        return []
    try:
        cutoff = (datetime.now(TZ).date() - timedelta(days=n - 1)).isoformat()
        res = sb.table("daily_runs").select("*").gte("date", cutoff).order("date", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Lecture daily_runs échouée : {e}")
        return []


# === API publique : persiste + publie ===

def update_daily_report_page(page_id: str, report: RunReport) -> bool:
    """Persiste le run du jour, puis republie la page Notion avec les 7 derniers."""
    if not page_id:
        return False

    report.finalize()

    # Coût du jour : récupéré depuis api_calls
    try:
        from observability.api_logger import fetch_recent_calls
        today_iso = report.start_time.date().isoformat()
        today_calls = [c for c in fetch_recent_calls(days=1) if c.get("date") == today_iso]
        report.cost_usd = sum(float(c.get("cost_estimate_usd") or 0) for c in today_calls)
    except Exception as e:
        logger.debug(f"Calcul coût quotidien échoué (non bloquant) : {e}")

    _persist_run(report)
    runs = _fetch_last_n_runs(7)

    try:
        notion = Client(auth=NOTION_API_KEY)
        blocks = _build_page_blocks(runs)
        _clear_page_blocks(notion, page_id)
        for chunk_start in range(0, len(blocks), 100):
            notion.blocks.children.append(block_id=page_id, children=blocks[chunk_start:chunk_start + 100])
        logger.info(f"Page Notion rapport quotidien mise à jour ({len(blocks)} blocs)")
        return True
    except Exception as e:
        logger.error(f"Echec MAJ page rapport quotidien : {type(e).__name__} : {e}")
        return False


def _clear_page_blocks(notion: Client, page_id: str) -> None:
    children = notion.blocks.children.list(block_id=page_id, page_size=100)
    for block in children.get("results", []):
        try:
            notion.blocks.delete(block_id=block["id"])
        except Exception as e:
            logger.debug(f"Suppression bloc {block['id']} échouée : {e}")


# === Construction des blocs Notion ===

def _build_page_blocks(runs: list[dict[str, Any]]) -> list[dict]:
    """Aujourd'hui détaillé en haut, jours précédents en toggles."""
    blocks: list[dict] = []
    blocks.append(_callout(
        f"🔄 Mis à jour le {datetime.now(TZ).strftime('%Y-%m-%d à %Hh%M')} (Europe/Paris)",
        emoji="🔄",
    ))

    if not runs:
        blocks.append(_paragraph("Aucun run enregistré pour le moment."))
        return blocks

    # Aujourd'hui = run le plus récent (déjà trié desc)
    today_run = runs[0]
    blocks.extend(_build_run_section(today_run, expanded=True))

    if len(runs) > 1:
        blocks.append(_divider())
        blocks.append(_heading_2("📚 Historique (6 derniers jours)"))
        for run in runs[1:]:
            blocks.append(_run_toggle(run))

    blocks.append(_divider())
    blocks.append(_paragraph(
        "Source : table Supabase `daily_runs`. "
        "Détail des appels API : `python report_api_usage.py --days 7 --by step`"
    ))
    return blocks


def _build_run_section(run: dict[str, Any], expanded: bool) -> list[dict]:
    """Section détaillée d'un run (utilisée pour 'aujourd'hui')."""
    blocks: list[dict] = []
    date_str = _fmt_date(run.get("date", ""))
    duration = run.get("duration_seconds") or 0
    published = run.get("published_count") or 0
    cost = float(run.get("cost_usd") or 0)

    blocks.append(_heading_1(f"📅 {date_str}"))

    # Synthèse (callout coloré selon résultat)
    if run.get("early_exit_reason"):
        # Pipeline a tourné correctement mais 0 image — afficher clairement
        # que ce n'est PAS un bug, et donner la raison précise.
        blocks.append(_callout(
            f"ℹ️ Pipeline OK — aucune infographie publiée aujourd'hui (ce n'est pas un bug)",
            emoji="ℹ️", color="blue_background",
        ))
        blocks.append(_callout(
            f"📌 Raison : {run['early_exit_reason']}\n"
            f"⏱️ Durée du run : {duration}s · 💵 Coût : ${cost:.3f}\n"
            f"✅ Aucune erreur technique — le pipeline a fait son travail et a estimé qu'il n'y avait rien à publier.",
            emoji="📋", color="gray_background",
        ))
    elif published == 0:
        blocks.append(_callout(
            f"ℹ️ 0 infographie publiée — pipeline OK, juste pas d'item retenu\n"
            f"Durée {duration}s · Coût ${cost:.3f}",
            emoji="ℹ️", color="blue_background",
        ))
    else:
        blocks.append(_callout(
            f"✅ {published} infographie(s) publiée(s) · "
            f"{run.get('carousel_slides_count') or 0} slide(s) carrousel\n"
            f"Durée {duration}s · Coût ${cost:.3f}",
            emoji="✅", color="green_background",
        ))

    # Phase 1 : collecte
    by_source = run.get("by_source") or {}
    total = run.get("total_collected") or 0
    blocks.append(_heading_3(f"📥 Collecte ({total} news)"))
    if by_source:
        for src, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
            blocks.append(_bullet(f"{src} : {n} item(s)"))
    else:
        blocks.append(_paragraph("(aucune source n'a remonté de news)"))

    # Phase 3 : scoring
    scoring = run.get("scoring") or []
    if scoring:
        blocks.append(_heading_3(f"🎯 Scoring viral (seuil = 7/10) — {len(scoring)} news scorées"))
        kept = [s for s in scoring if s.get("kept")]
        rejected = [s for s in scoring if not s.get("kept")]
        if kept:
            blocks.append(_paragraph(f"✅ Retenues ({len(kept)}) :"))
            for s in kept:
                blocks.append(_bullet(
                    f"[{s.get('score', '?')}/10] {s.get('title', '')[:100]} — "
                    f"{s.get('source', '')} · {s.get('reason', '')[:140]}"
                ))
        if rejected:
            blocks.append(_paragraph(f"❌ Rejetées ({len(rejected)}) :"))
            for s in rejected:
                blocks.append(_bullet(
                    f"[{s.get('score', '?')}/10] {s.get('title', '')[:100]} — "
                    f"{s.get('source', '')} · {s.get('reason', '')[:140]}"
                ))

    # Phase 3.5 : éditorial
    editorial = run.get("editorial") or {}
    if editorial:
        sel_count = editorial.get("selected_count", 0)
        rej_titles = editorial.get("rejected_titles") or []
        blocks.append(_heading_3(f"✍️ Direction éditoriale — {sel_count} infographies finales"))
        if editorial.get("selected_titles"):
            for title, angle in zip(editorial["selected_titles"], editorial.get("selected_angles") or []):
                blocks.append(_bullet(f"[{angle}] {title[:140]}"))
        if rej_titles:
            blocks.append(_paragraph(f"❌ Rejetées par l'éditorial ({len(rej_titles)}) :"))
            for t in rej_titles:
                blocks.append(_bullet(t[:140]))
        if editorial.get("reasoning"):
            blocks.append(_callout(
                f"Raisonnement éditorial : {editorial['reasoning'][:600]}",
                emoji="💭", color="default",
            ))

    return blocks


def _run_toggle(run: dict[str, Any]) -> dict:
    """Bloc toggle (repliable) pour un run précédent."""
    date_str = _fmt_date(run.get("date", ""))
    published = run.get("published_count") or 0
    cost = float(run.get("cost_usd") or 0)
    if run.get("early_exit_reason"):
        emoji = "ℹ️"
        summary = f"Pipeline OK — {run['early_exit_reason'][:70]}"
    elif published == 0:
        emoji = "ℹ️"
        summary = "Pipeline OK — 0 infographie publiée"
    else:
        emoji = "✅"
        summary = f"{published} infographie(s) publiée(s)"

    title = f"{emoji} {date_str} — {summary} · ${cost:.3f}"

    # Le contenu interne du toggle = section détaillée (sans le H1 du jour)
    inner = _build_run_section(run, expanded=False)
    # On retire le premier bloc (H1 date) car le toggle a déjà la date dans son titre
    inner = [b for b in inner if b.get("type") != "heading_1"]

    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": title}}],
            "children": inner[:100],  # Notion limite à 100 enfants
        },
    }


# === Helpers blocs Notion ===

def _heading_1(text: str) -> dict:
    return {"object": "block", "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def _heading_2(text: str) -> dict:
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def _heading_3(text: str) -> dict:
    return {"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def _bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def _callout(text: str, emoji: str = "💡", color: str = "default") -> dict:
    return {"object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "icon": {"type": "emoji", "emoji": emoji},
                "color": color,
            }}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _fmt_date(iso: str) -> str:
    """2026-04-27 -> 'lundi 27 avril 2026'."""
    if not iso:
        return "(date inconnue)"
    try:
        d = datetime.fromisoformat(iso).date()
        days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        months = ["janvier", "février", "mars", "avril", "mai", "juin",
                  "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        return f"{days[d.weekday()]} {d.day} {months[d.month - 1]} {d.year}"
    except Exception:
        return iso
