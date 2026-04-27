"""Enrichissement du contenu d'une news pour produire le JSON structuré
attendu par le template d'infographie cyan.

Workflow par news :
1. Claude Sonnet 4.6 reçoit la news (titre + résumé)
2. Claude utilise le tool web_search Anthropic pour faire 2-3 recherches
   (contexte produit, citations, chiffres, dates précises)
3. Claude produit un JSON structuré conforme au template :
   { titre, sous_titre, keywords_cyan, stat, stat_desc, blocs[] }
4. Validation des contraintes (longueurs max), fallback minimal si échec
"""
import json
import logging
import time
from typing import Any, List

from anthropic import Anthropic

from config.models import NewsItem
from config.settings import ANTHROPIC_API_KEY, AUDIENCE_DESCRIPTION, CLAUDE_MODEL, TOPIC_DESCRIPTION, TOPIC_NAME
from observability.api_logger import log_api_call

logger = logging.getLogger(__name__)

# Outil web_search d'Anthropic. max_uses=3 pour limiter les coûts
# (~0.01 $/recherche + tokens supplémentaires).
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,
}

# Le prompt d'enrichissement ci-dessous est conçu pour produire un JSON
# strictement conforme au template d'infographie magazine cyan.
ENRICHMENT_PROMPT = """Tu es rédacteur éditorial pour un média francophone d'actualité {topic_description}.

{audience}

Voici une news à transformer en infographie magazine éditoriale.

NEWS :
Source : {source}
Titre : {title}
Résumé brut (peut être incomplet) : {summary}
URL : {url}
Angle éditorial proposé : {angle}

ANGLE ÉDITORIAL IMPOSÉ (décidé par le chef éditorial en amont) :
Type : {angle_type}
Brief directeur : {brief}

STRUCTURE ATTENDUE DES 6 BLOCS SELON L'ANGLE TYPE :
- analyse_outil : 01 ce que c'est / 02 ce qui change / 03 cas d'usage indés / 04 vs concurrence / 05 limites / 06 à savoir avant d'adopter
- tutoriel : 01 prérequis / 02 étape 1 / 03 étape 2 / 04 étape 3 / 05 astuce pro / 06 limite ou piège à éviter
- decryptage : 01 ce qui est annoncé / 02 ce qu'on ne dit pas / 03 vrais gagnants / 04 vrais perdants / 05 zone grise / 06 ta lecture (take)
- impact_business : 01 ce qui se passe / 02 pour qui c'est pertinent / 03 gain / économie chiffré / 04 nouveau flux de travail / 05 à surveiller / 06 action concrète à prendre
- comparaison : 01 contexte / 02 A vs B critère 1 / 03 A vs B critère 2 / 04 quand préférer A / 05 quand préférer B / 06 verdict
- debrief : 01 contexte / 02 annonce principale / 03 chiffres clés / 04 réactions du marché / 05 limites / 06 ce qui vient ensuite

Respecte STRICTEMENT cet ordre et cette logique pour les 6 blocs. Le brief directeur ci-dessus oriente le fond ; la structure vient de l'angle type.

ÉTAPE 1 — RECHERCHE WEB (obligatoire)
Utilise l'outil web_search pour enrichir ton contexte. Fais 2 à 3 recherches ciblées :
- Une recherche pour confirmer les faits clés et trouver des chiffres précis
- Une recherche pour identifier des citations ou prises de position
- Une recherche pour trouver des cas d'usage concrets ou comparaisons

ÉTAPE 2 — PRODUCTION DU JSON STRUCTURÉ
Produis un JSON strictement conforme au schéma ci-dessous. Tout doit être en français,
avec accents parfaits, sans emoji, sans tirets cadratins.

SCHÉMA EXACT (respecte les longueurs max, sinon le rendu visuel sera cassé) :

{{
  "titre": "TITRE EN MAJUSCULES AVEC ACCENTS",           // max 24 caractères
  "sous_titre": "Phrase descriptive avec keywords",      // max 75 caractères
  "keywords_cyan": ["mot1", "mot2"],                     // 1-3 mots du sous_titre à mettre en cyan
  "stat": "73%",                                         // une stat marquante. Si pas de chiffre, utilise "NOUVEAU"
  "stat_desc": "des freelances l'utilisent au quotidien",// max 40 caractères
  "blocs": [                                             // EXACTEMENT 6 blocs
    {{
      "numero": "01",
      "titre": "TITRE BLOC EN MAJUSCULES AVEC ACCENTS",  // max 32 caractères
      "points": [                                        // EXACTEMENT 4 puces
        "Phrase courte et concrète",                     // max 48 caractères chacune
        "Deuxième info concrète",
        "Troisième info chiffrée",
        "Quatrième info actionnable"
      ],
      "exemple": "Cas concret en une phrase italique"    // optionnel mais recommandé, max 70 chars
    }},
    {{ "numero": "02", ...  }},
    ...
    {{ "numero": "06", ...  }}
  ]
}}

RÈGLES DE LONGUEUR (CRITIQUE — le moindre dépassement coupe visuellement le mot dans l'image rendue) :
- VISE 40 CHARS par puce, pas 48. Ne joue jamais à la limite max.
- Privilégie les phrases TÉLÉGRAPHIQUES : verbe d'action + chiffre + mot-clé. Pas d'articles superflus, pas de connecteurs ("ainsi", "par ailleurs", "notamment", "désormais").
- Si une info riche ne tient pas en 48 chars, COUPE l'info au lieu de la condenser jusqu'à la limite. Mieux vaut une puce courte percutante qu'une puce dense tronquée.
- Termes anglais (Business, ChatGPT, OpenAI, Anthropic) sont des mots indivisibles : vérifie qu'ils ne sont jamais en fin de ligne près de la limite max.
- Exemple BIEN : "82,7 % vs 69,4 % sur workflows longs" (37 chars, télégraphique)
- Exemple MAL : "82,7 % de précision sur les workflows longs contre 69,4 %" (59 chars, trop long, "%" coupé visuellement)
- Idem pour titre, sous_titre, exemple : reste sous 80 % de la limite max.

RÈGLE CRITIQUE SUR LES ACCENTS FRANÇAIS :
Tu DOIS conserver TOUS les accents français dans les textes (é è ê ë à â ä ç ï î ô ö û ù ü ÿ œ æ),
y compris dans les mots en MAJUSCULES. Exemples obligatoires :
- "LÀ" pas "LA", "À" pas "A" (quand c'est la préposition)
- "MODÈLE" pas "MODELE", "CONNAÎTRE" pas "CONNAITRE"
- "RÉFLÉCHIR" pas "REFLECHIR", "DÉJÀ" pas "DEJA"
- "TÂCHES" pas "TACHES", "INDÉPENDANTS" pas "INDEPENDANTS"
- "RÉALISÉES" pas "REALISEES", "CRÉATIVITÉ" pas "CREATIVITE"
Les accents doivent être rendus dans le JSON comme caractères Unicode normaux (é, è, à, etc.),
pas en HTML entities, pas avec des backslashes. Le texte sans accents sera rejeté.

RÈGLES CONTENU :
- Les 6 blocs doivent former une lecture cohérente : qu'est-ce que c'est, pourquoi c'est important,
  comment l'utiliser, comparaison avec l'existant, cas d'usage, limites/à savoir.
- Privilégie l'angle pragmatique pour freelances/coachs/consultants (pas un papier de recherche).
- Les puces doivent être actionnables ou informatives (jamais de blabla générique).
- Les exemples doivent être réels et issus de tes recherches web (pas inventés).
- Si la news est trop pauvre pour 6 blocs riches, fais 4 blocs maximum (et adapte le tableau).

RÈGLES FORMAT :
- Réponds UNIQUEMENT avec le JSON valide, sans markdown, sans prose autour.
- Pas d'emoji, pas de tirets cadratins (—), utilise le point ou la virgule.
- Texte court et impactant (le but : tenir dans une infographie A4).

Génère maintenant le JSON après tes recherches web."""


def enrich_news_content(items: List[NewsItem]) -> List[NewsItem]:
    """Enrichit chaque news avec un JSON structuré pour l'infographie.

    Si l'enrichissement échoue pour une news (web search bloqué, JSON invalide),
    on génère un JSON minimal de fallback à partir du titre + summary.
    """
    if not items:
        return []

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    for i, item in enumerate(items):
        logger.info(f"Enrichissement {i+1}/{len(items)} : {item.title[:60]}")
        try:
            structured = _enrich_one(client, item)
            item.structured_content = structured
            logger.info(
                f"  -> {len(structured.get('blocs', []))} blocs, "
                f"stat={structured.get('stat')}, sources web={len(item.web_sources)}"
            )
        except Exception as e:
            logger.error(f"Echec enrichissement '{item.title[:60]}' : {type(e).__name__} : {e}")
            item.structured_content = _fallback_content(item)
            logger.info("  -> fallback minimal utilisé")

    return items


def _enrich_one(client: Anthropic, item: NewsItem) -> dict[str, Any]:
    """Appelle Claude avec web_search puis parse le JSON structuré."""
    prompt = ENRICHMENT_PROMPT.format(
        audience=AUDIENCE_DESCRIPTION,
        topic_description=TOPIC_DESCRIPTION,
        source=item.source,
        title=item.title,
        summary=item.summary[:5000],
        url=item.url,
        angle=item.editorial_angle or "(à déterminer)",
        angle_type=item.editorial_angle_type or "analyse_outil",
        brief=item.editorial_brief or "(brief libre, produit l'infographie la plus pertinente)",
    )

    t0 = time.perf_counter()
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log_api_call(
            provider="anthropic",
            model=CLAUDE_MODEL,
            operation="messages.create",
            duration_ms=int((time.perf_counter() - t0) * 1000),
            success=False,
            error=str(e),
            context={"step": "enrichment", "news_title": item.title[:60]},
        )
        raise

    duration_ms = int((time.perf_counter() - t0) * 1000)

    # Le response.content peut contenir : plusieurs text blocks (Claude commente parfois
    # entre ses recherches), server_tool_use, web_search_tool_result.
    # On collecte tous les text blocks et toutes les URLs sources, puis on cherche
    # le bloc qui contient un JSON (commence par '{' après strip et nettoyage markdown).
    text_blocks: list[str] = []
    web_sources: list[str] = []
    n_web_searches = 0

    for block in response.content:
        btype = getattr(block, "type", None)
        if btype == "text":
            text_blocks.append(block.text or "")
        elif btype == "server_tool_use":
            # Compte le nombre de recherches web réellement effectuées
            n_web_searches += 1
        elif btype == "web_search_tool_result":
            results = getattr(block, "content", [])
            if isinstance(results, list):
                for r in results:
                    url = getattr(r, "url", None) or (r.get("url") if isinstance(r, dict) else None)
                    if url:
                        web_sources.append(url)

    item.web_sources = web_sources

    # Log l'appel principal Claude
    log_api_call(
        provider="anthropic",
        model=CLAUDE_MODEL,
        operation="messages.create",
        duration_ms=duration_ms,
        success=True,
        input_tokens=getattr(response.usage, "input_tokens", None),
        output_tokens=getattr(response.usage, "output_tokens", None),
        context={
            "step": "enrichment",
            "news_title": item.title[:60],
            "n_web_searches": n_web_searches,
        },
    )

    # Log séparément chaque utilisation du tool web_search (facturé à part par Anthropic)
    for _ in range(n_web_searches):
        log_api_call(
            provider="anthropic",
            model="web_search_20250305",
            operation="server_tool_use",
            duration_ms=0,
            success=True,
            context={"step": "enrichment", "news_title": item.title[:60]},
        )

    json_text = _extract_json(text_blocks)
    if not json_text:
        # Diagnostic : log les blocs reçus pour debug
        logger.warning(f"Aucun JSON trouvé dans la réponse. Text blocks reçus :")
        for i, t in enumerate(text_blocks):
            logger.warning(f"  block {i} ({len(t)} chars) : {t[:200]!r}")
        raise ValueError("Pas de JSON dans la réponse Claude")

    data = json.loads(json_text)
    return _validate_structured(data, item)


def _extract_json(text_blocks: list[str]) -> str:
    """Trouve dans les text blocks celui qui contient un objet JSON.

    Stratégie : on parcourt les blocs en partant du DERNIER (le JSON est généralement
    en fin de réponse), on nettoie le markdown éventuel, et on prend le premier qui
    commence par '{' et finit par '}'.
    """
    for raw in reversed(text_blocks):
        candidate = raw.strip()
        # Strip markdown code fences ```json ... ```
        if candidate.startswith("```"):
            candidate = candidate.split("```")[1]
            if candidate.lstrip().startswith("json"):
                candidate = candidate.lstrip()[4:]
            candidate = candidate.strip()
        # Strip markdown code fence in the middle
        if "```json" in raw:
            try:
                candidate = raw.split("```json", 1)[1].split("```", 1)[0].strip()
            except IndexError:
                pass
        if candidate.startswith("{") and candidate.rstrip().endswith("}"):
            return candidate
    return ""


def _validate_structured(data: dict[str, Any], item: NewsItem) -> dict[str, Any]:
    """Valide / nettoie les contraintes de longueur. Tronque sans crasher."""
    out = {
        "titre": (data.get("titre") or item.title)[:24].upper(),
        "sous_titre": (data.get("sous_titre") or "")[:75],
        "keywords_cyan": [str(k)[:30] for k in (data.get("keywords_cyan") or [])][:3],
        "stat": str(data.get("stat") or "NOUVEAU")[:8],
        "stat_desc": (data.get("stat_desc") or "")[:40],
        "blocs": [],
    }

    blocs_raw = data.get("blocs") or []
    for b in blocs_raw[:6]:
        bloc = {
            "numero": str(b.get("numero", "")).zfill(2)[:2],
            "titre": (b.get("titre") or "")[:32].upper(),
            "points": [str(p)[:48] for p in (b.get("points") or [])][:4],
            "exemple": (b.get("exemple") or "")[:70],
        }
        # Ne garder que les blocs avec au moins 2 puces (sinon visuellement vide)
        if len(bloc["points"]) >= 2:
            out["blocs"].append(bloc)

    if len(out["blocs"]) < 1:
        # Trop pauvre, fallback
        return _fallback_content(item)
    return out


def _fallback_content(item: NewsItem) -> dict[str, Any]:
    """JSON minimal généré sans appel API, si l'enrichissement échoue."""
    short_title = item.title[:30].upper()
    return {
        "titre": short_title,
        "sous_titre": (item.editorial_angle or item.title)[:90],
        "keywords_cyan": [],
        "stat": "NOUVEAU",
        "stat_desc": f"Actualité {TOPIC_NAME} du jour",
        "blocs": [
            {
                "numero": "01",
                "titre": "EN BREF",
                "points": [
                    item.title[:60],
                    item.source[:60],
                    f"Actualité {TOPIC_NAME} du jour",
                    "Voir source pour détails",
                ],
                "exemple": "",
            }
        ],
    }
