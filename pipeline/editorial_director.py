"""Chef éditorial : clustering sémantique + attribution d'angle par news.

Après le scoring viral, plusieurs news peuvent couvrir le même sujet (ex: 3 news
différentes sur "ChatGPT Images 2.0"). Sans cette étape, le pipeline produisait
3 infographies quasi-identiques. Le chef éditorial :

1. Regroupe les news parlant du même sujet
2. Décide FUSION (1 seule infographie synthèse) ou DISTINCTION (plusieurs
   infographies avec des angles différents)
3. Attribue à chaque item final un angle type + un brief directeur
4. Rejette les news hors audience
5. Plafonne à 4-6 items (au lieu des 10 en sortie du scoring)

Un seul appel Claude Sonnet 4.6 avec le batch complet.
"""
import copy
import json
import logging
import time
from typing import Any, List

from anthropic import Anthropic

from config.models import NewsItem
from config.settings import ANTHROPIC_API_KEY, AUDIENCE_DESCRIPTION, CLAUDE_MODEL, TOPIC_DESCRIPTION
from observability.api_logger import log_api_call
from pipeline.run_report import RunReport

logger = logging.getLogger(__name__)

# Valeurs valides pour editorial_angle_type. Toute autre valeur sera remplacée
# par analyse_outil (défaut safe).
VALID_ANGLE_TYPES = {
    "analyse_outil",
    "tutoriel",
    "decryptage",
    "impact_business",
    "comparaison",
    "debrief",
}

MAX_FINAL_ITEMS = 6  # plafond dur sur le nombre d'infographies après merge


EDITORIAL_PROMPT = """Tu es rédacteur en chef d'un média francophone d'actualité {topic_description} pour freelances, coachs et consultants indépendants.

{audience}

Tu reçois un batch de news scorées par un système automatique (score de 1 à 10). Ton rôle est de BÂTIR la ligne éditoriale du jour : regrouper les news redondantes, varier les angles, rejeter ce qui est hors cible, et produire entre 3 et {max_items} INFOGRAPHIES distinctes, cohérentes et complémentaires.

BATCH DE NEWS EN ENTRÉE ({n} news) :

{news_text}

RÈGLES DE DÉCISION :

1. CLUSTERING : identifie les news qui parlent du MÊME sujet (ex: 3 news qui toutes parlent de ChatGPT Images 2.0). Pour chaque cluster, décide :
   - FUSION si les news redisent à peu près la même chose → 1 seule infographie qui synthétise, avec merged_title clair et merged_summary combiné.
   - DISTINCTION si les news apportent des angles réellement différents → plusieurs infographies, chacune avec un angle type DIFFÉRENT.

2. ANGLES ÉDITORIAUX : attribue à chaque infographie finale un angle type parmi ces 6 valeurs EXACTES :
   - "analyse_outil" : décrypter ce qu'apporte un nouvel outil/modèle (cas le plus fréquent)
   - "tutoriel" : comment utiliser, étapes pratiques
   - "decryptage" : ce qui est annoncé vs ce qui est réellement en jeu (politique, business)
   - "impact_business" : conséquences concrètes pour l'audience indépendants
   - "comparaison" : outil A vs B, ancien vs nouveau, force vs limite
   - "debrief" : résumé factuel d'une annonce brute (quand la news est juste "c'est sorti")

3. EDITORIAL BRIEF : pour chaque infographie, rédige une phrase directrice (max 200 chars) qui guidera la création du contenu. Exemple :
   "Décrypter ce que ChatGPT Images 2.0 change concrètement pour les freelances : génération de visuels avec texte FR propre, carrousels cohérents, cas d'usage en une journée"

4. REJET : écarte sans pitié les news qui ne collent pas à l'audience ou qui sortent du sujet "{topic_description}" :
   - Papers de recherche pure, résultats académiques
   - News business / célébrités sans lien avec le sujet (HORS SUJET)
   - News politiques / drama sans impact concret
   - Sujets trop niche pour des experts pointus uniquement

5. VARIÉTÉ : si deux news reçoivent le MÊME angle type, assure-toi qu'elles traitent de sujets RÉELLEMENT différents. Ne mets jamais 3 "analyse_outil" sur des sujets proches — varie.

6. PLAFOND : entre 3 et {max_items} infographies finales. Si le batch est pauvre, 3 suffit. Jamais plus de {max_items}.

RÉPONDS UNIQUEMENT AVEC CE JSON VALIDE (pas de markdown, pas de prose) :

{{
  "selected": [
    {{
      "source_indices": [0, 3, 7],                  // indices des news fusionnées depuis le batch d'entrée
      "merged_title": "ChatGPT Images 2.0",         // titre propre en français, max 80 chars
      "merged_summary": "...",                       // résumé consolidé qui combine les infos clés, max 2000 chars
      "editorial_angle_type": "analyse_outil",
      "editorial_brief": "Décrypter..."              // max 200 chars
    }}
  ],
  "rejected_indices": [5, 8],                       // indices des news écartées
  "reasoning": "3 news redondantes sur ChatGPT Images fusionnées, Tim Cook rejeté car HS audience freelance, etc."
}}

Règles JSON : tous les accents français préservés, pas d'emoji, pas de tirets cadratins."""


def direct_editorial(items: List[NewsItem], report: RunReport | None = None) -> List[NewsItem]:
    """Applique la direction éditoriale au batch de news scorées.

    En cas d'échec, retourne les items d'origine avec editorial_angle_type
    par défaut ("analyse_outil") pour ne pas bloquer le pipeline.

    Si `report` est fourni, y pousse la décision éditoriale (selected, rejected,
    reasoning) pour le rapport quotidien Notion.
    """
    if not items:
        return []

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Préparer le texte du batch pour Claude
    blocks = []
    for i, item in enumerate(items):
        blocks.append(
            f"[{i}] SCORE:{item.viral_score or 0}/10 | SOURCE:{item.source}\n"
            f"    TITRE: {item.title}\n"
            f"    ANGLE_SCORING: {item.editorial_angle}\n"
            f"    RESUME: {item.summary[:400]}\n"
        )
    news_text = "\n".join(blocks)

    prompt = EDITORIAL_PROMPT.format(
        audience=AUDIENCE_DESCRIPTION,
        topic_description=TOPIC_DESCRIPTION,
        n=len(items),
        max_items=MAX_FINAL_ITEMS,
        news_text=news_text,
    )

    t0 = time.perf_counter()
    try:
        logger.info(f"Direction éditoriale sur {len(items)} news scorées...")
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
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
            context={"step": "editorial_direction", "n_news": len(items)},
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        data = json.loads(text)
    except Exception as e:
        log_api_call(
            provider="anthropic",
            model=CLAUDE_MODEL,
            operation="messages.create",
            duration_ms=int((time.perf_counter() - t0) * 1000),
            success=False,
            error=str(e),
            context={"step": "editorial_direction", "n_news": len(items)},
        )
        logger.error(f"Echec chef éditorial ({type(e).__name__}: {e}), fallback items d'origine")
        for it in items:
            it.editorial_angle_type = "analyse_outil"
        return items

    selected = data.get("selected") or []
    rejected = data.get("rejected_indices") or []
    reasoning = data.get("reasoning", "")

    logger.info(
        f"Chef éditorial : {len(selected)} infographies finales, "
        f"{len(rejected)} rejetées (raison : {reasoning[:150]})"
    )

    final_items: list[NewsItem] = []
    for entry in selected[:MAX_FINAL_ITEMS]:
        item = _reconstruct_item(entry, items)
        if item:
            final_items.append(item)

    # Pousser la décision au RunReport
    if report is not None:
        report.set_editorial({
            "selected_count": len(final_items),
            "selected_titles": [it.title[:200] for it in final_items],
            "selected_angles": [it.editorial_angle_type for it in final_items],
            "rejected_indices": rejected,
            "rejected_titles": [items[i].title[:200] for i in rejected if 0 <= i < len(items)],
            "reasoning": (reasoning or "")[:1000],
        })

    if not final_items:
        logger.warning("Aucun item reconstruit, fallback items d'origine")
        for it in items:
            it.editorial_angle_type = "analyse_outil"
        return items

    return final_items


def _reconstruct_item(entry: dict[str, Any], source_items: list[NewsItem]) -> NewsItem | None:
    """Construit un NewsItem final à partir d'une entrée JSON selected du chef édito.

    Stratégie :
    - Base = première news du cluster (pour garder published_at, score)
    - Override title / summary / editorial_angle_type / editorial_brief
    - Aggrège les URLs des news sources dans merged_from_urls
    """
    indices = entry.get("source_indices") or []
    if not indices:
        return None

    base = None
    urls: list[str] = []
    for idx in indices:
        if 0 <= idx < len(source_items):
            src = source_items[idx]
            if base is None:
                base = copy.copy(src)
            if src.url and src.url not in urls:
                urls.append(src.url)

    if base is None:
        return None

    merged_title = (entry.get("merged_title") or base.title)[:200]
    merged_summary = (entry.get("merged_summary") or base.summary)[:2000]
    angle_type = entry.get("editorial_angle_type") or "analyse_outil"
    if angle_type not in VALID_ANGLE_TYPES:
        logger.warning(f"Angle type invalide '{angle_type}', fallback analyse_outil")
        angle_type = "analyse_outil"
    brief = (entry.get("editorial_brief") or "")[:200]

    base.title = merged_title
    base.summary = merged_summary
    base.editorial_angle_type = angle_type
    base.editorial_brief = brief
    base.merged_from_urls = urls

    logger.info(
        f"  - [{len(indices)} news -> 1] angle={angle_type} | titre='{merged_title[:60]}'"
    )
    return base
