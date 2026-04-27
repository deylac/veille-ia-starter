"""Publication des news + images dans Notion.

Workflow :
1. Upload de l'image vers Supabase Storage (bucket public)
2. Création d'une page Notion avec l'image en cover + propriétés remplies
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

import requests
from notion_client import Client
from supabase import Client as SupabaseClient
from supabase import create_client

from config.models import NewsItem
from config.settings import BRAND_NAME, NOTION_API_KEY, NOTION_DATABASE_ID, TZ

logger = logging.getLogger(__name__)

# Supabase pour héberger les images
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # service key, pas anon
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "veille-images")


def push_to_notion(items: List[NewsItem]) -> int:
    """Crée une page Notion par item. Retourne le nombre de pages créées."""
    if not items:
        return 0

    notion = Client(auth=NOTION_API_KEY)
    supabase = _init_supabase()

    created = 0
    for item in items:
        try:
            # 1. Upload de l'image
            image_url = ""
            if item.image_path and supabase:
                image_url = _upload_image(supabase, item.image_path)

            # 2. Création de la page Notion
            properties = _build_properties(item, image_url)
            children = _build_page_content(item)

            page_args = {
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": properties,
                "children": children,
            }
            if image_url:
                page_args["cover"] = {"type": "external", "external": {"url": image_url}}

            notion.pages.create(**page_args)
            created += 1
            logger.info(f"Page Notion créée : {item.title[:60]}")

        except Exception as e:
            logger.error(f"Erreur création page Notion pour '{item.title[:60]}' : {e}")

    return created


def push_carousel_to_notion(slide_paths: list[str], carousel_meta: dict) -> bool:
    """Crée 1 page Notion "Carrousel JJ/MM" avec toutes les slides attachées.

    Structure de la page :
    - Cover = slide 0 (la cover du carrousel)
    - Propriété Image générée = toutes les slides en lot
    - Blocs de contenu = chaque slide affichée en gros dans la page
    """
    if not slide_paths:
        logger.warning("Aucune slide à pousser dans Notion pour le carrousel")
        return False

    notion = Client(auth=NOTION_API_KEY)
    supabase = _init_supabase()

    # 1. Upload toutes les slides vers Supabase (en parallèle virtuellement, séquentiel ici)
    slide_urls: list[str] = []
    for path in slide_paths:
        url = _upload_image(supabase, path) if supabase else ""
        if url:
            slide_urls.append(url)

    if not slide_urls:
        logger.error("Aucune slide uploadée, impossible de créer la page Notion")
        return False

    cover_url = slide_urls[0]
    date_long = carousel_meta.get("date", "")
    date_short = carousel_meta.get("date_short", "")

    # 2. Propriétés de la page
    properties = {
        "Titre": {
            "title": [{"text": {"content": f"Carrousel du {date_short} — {date_long}"[:2000]}}],
        },
        "Source": {"select": {"name": BRAND_NAME[:100]}},
        "Score viral": {"number": 10},  # Un carrousel = top du top
        "Format utilisé": {"select": {"name": "carrousel"}},
        "Type de document": {"select": {"name": "carrousel"}},
        "Statut": {"select": {"name": "À valider"}},
        "Date scan": {"date": {"start": datetime.now(TZ).date().isoformat()}},
        "Image générée": {
            "files": [
                {
                    "name": f"slide_{i:02d}.png",
                    "type": "external",
                    "external": {"url": url},
                }
                for i, url in enumerate(slide_urls)
            ]
        },
        "Angle éditorial": {
            "rich_text": [
                {"text": {"content": f"Carrousel Instagram {len(slide_urls)} slides"[:2000]}}
            ]
        },
    }

    # 3. Blocs de contenu : chaque slide affichée en grande image
    children: list[dict] = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": f"Carrousel {date_long}"}}]
            },
        }
    ]
    for i, url in enumerate(slide_urls):
        kind = "Cover" if i == 0 else ("Outro" if i == len(slide_urls) - 1 else f"Slide {i:02d}")
        children.append(
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": kind}}]},
            }
        )
        children.append(
            {
                "object": "block",
                "type": "image",
                "image": {"type": "external", "external": {"url": url}},
            }
        )

    try:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties,
            cover={"type": "external", "external": {"url": cover_url}},
            children=children,
        )
        logger.info(f"Page Notion carrousel créée : {len(slide_urls)} slides attachées")
        return True
    except Exception as e:
        logger.error(f"Erreur création page carrousel : {type(e).__name__} : {e}")
        return False


def _init_supabase() -> SupabaseClient | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase non configuré, les images ne seront pas attachées aux pages Notion")
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Erreur init Supabase : {e}")
        return None


def _upload_image(supabase: SupabaseClient, local_path: str) -> str:
    """Upload une image locale vers Supabase Storage et retourne l'URL publique."""
    path = Path(local_path)
    if not path.exists():
        return ""

    # Nom unique : YYYYMMDD-HHMMSS-filename
    timestamp = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
    storage_path = f"{timestamp}-{path.name}"

    try:
        with open(path, "rb") as f:
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                path=storage_path,
                file=f.read(),
                file_options={"content-type": "image/png", "upsert": "true"},
            )
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)
        return public_url
    except Exception as e:
        logger.error(f"Erreur upload Supabase : {e}")
        return ""


def _build_properties(item: NewsItem, image_url: str) -> dict:
    """Construit les propriétés de la page Notion."""
    properties = {
        "Titre": {
            "title": [{"text": {"content": item.title[:2000]}}],
        },
        "Source": {
            "select": {"name": _truncate_select(item.source)},
        },
        "URL source": {
            "url": item.url[:2000] if item.url else None,
        },
        "Score viral": {
            "number": item.viral_score or 0,
        },
        "Format utilisé": {
            "select": {"name": "infographie"},
        },
        "Type de document": {
            "select": {"name": "infographie"},
        },
        "Hook suggéré FR": {
            "rich_text": [{"text": {"content": (item.hook_fr or "")[:2000]}}],
        },
        "Angle éditorial": {
            "rich_text": [{"text": {"content": (item.editorial_angle or "")[:2000]}}],
        },
        "Statut": {
            "select": {"name": "À valider"},
        },
        "Date scan": {
            "date": {"start": datetime.now(TZ).date().isoformat()},
        },
    }
    if image_url:
        properties["Image générée"] = {
            "files": [
                {
                    "name": Path(item.image_path).name if item.image_path else "image.png",
                    "type": "external",
                    "external": {"url": image_url},
                }
            ]
        }
    return properties


def _build_page_content(item: NewsItem) -> list:
    """Construit le corps de la page Notion (résumé, justification du score, etc.)."""
    blocks = []

    if item.viral_reason:
        blocks.append(_heading("Pourquoi cette news"))
        blocks.append(_paragraph(item.viral_reason))

    if item.summary:
        blocks.append(_heading("Résumé de la news"))
        blocks.append(_paragraph(item.summary[:2000]))

    if item.image_prompt:
        blocks.append(_heading("Prompt utilisé pour l'image"))
        blocks.append(_paragraph(item.image_prompt[:2000]))

    return blocks


def _heading(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _truncate_select(text: str) -> str:
    """Notion limite les options de Select à 100 caractères."""
    return text[:100]
