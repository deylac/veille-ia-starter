"""Scan des newsletters IA via Gmail API.

Pour la mise en place, voir NOTION_SETUP.md (section Gmail).
On utilise OAuth2 avec un refresh token persistant.
"""
import base64
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.models import NewsItem
from config.settings import GMAIL_TOKEN_PATH, LOOKBACK_HOURS, NEWSLETTER_SENDERS

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def fetch_newsletter_news() -> List[NewsItem]:
    """Récupère les newsletters récentes des expéditeurs surveillés."""
    creds = _load_credentials()
    if not creds:
        logger.warning("Gmail non configuré, skip newsletters")
        return []

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f"Erreur connexion Gmail : {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    # Format Gmail : after:YYYY/MM/DD
    after_date = cutoff.strftime("%Y/%m/%d")
    items: List[NewsItem] = []

    for sender in NEWSLETTER_SENDERS:
        query = f"from:{sender} after:{after_date}"
        try:
            logger.info(f"Scan Gmail : {sender}")
            results = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
            messages = results.get("messages", [])

            for msg_ref in messages:
                msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
                news_items = _parse_newsletter(msg, sender)
                items.extend(news_items)
        except Exception as e:
            logger.warning(f"Erreur Gmail {sender} : {e}")

    logger.info(f"Newsletters : {len(items)} items extraits")
    return items


def _load_credentials() -> Credentials | None:
    """Charge les credentials OAuth depuis le token JSON."""
    try:
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Sauvegarder le token rafraîchi
            with open(GMAIL_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        return creds
    except FileNotFoundError:
        logger.warning(f"Token Gmail introuvable : {GMAIL_TOKEN_PATH}")
        return None
    except Exception as e:
        logger.error(f"Erreur chargement creds Gmail : {e}")
        return None


def _parse_newsletter(msg: dict, sender: str) -> List[NewsItem]:
    """Extrait des items individuels d'une newsletter.

    Stratégie simple : on prend le sujet de l'email comme un seul item.
    Pour aller plus loin, on pourrait extraire chaque section/lien et créer un NewsItem par section.
    Ici on garde simple : 1 newsletter = 1 NewsItem (Claude lira le résumé pour scorer).
    """
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("Subject", "")
    date_str = headers.get("Date", "")
    try:
        published = parsedate_to_datetime(date_str)
    except (TypeError, ValueError):
        published = None

    body = _extract_body(msg["payload"])
    # Garder seulement les 3000 premiers caractères du body pour le scoring
    body = body[:3000]

    return [
        NewsItem(
            title=subject,
            url=f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
            source=f"Newsletter {sender.split('@')[0]}",
            summary=body,
            published_at=published,
        )
    ]


def _extract_body(payload: dict) -> str:
    """Extrait récursivement le corps texte d'un email Gmail."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return _decode(data)

    if "parts" in payload:
        for part in payload["parts"]:
            text = _extract_body(part)
            if text:
                return text

    # Fallback HTML
    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = _decode(data)
            import re

            return re.sub(r"<[^>]+>", " ", html)

    return ""


def _decode(b64_data: str) -> str:
    try:
        return base64.urlsafe_b64decode(b64_data).decode("utf-8", errors="ignore")
    except Exception:
        return ""
