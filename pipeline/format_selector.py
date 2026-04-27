"""Sélection du format visuel et construction du prompt Gemini.

Les 4 formats prédéfinis sont décrits dans des templates de prompt qui
poussent Gemini vers un rendu cohérent et professionnel.
"""
import json
import logging
import time
from typing import List

from anthropic import Anthropic

from config.models import NewsItem
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
from observability.api_logger import log_api_call

logger = logging.getLogger(__name__)


# Description des formats pour Claude (l'aide à choisir)
FORMAT_DESCRIPTIONS = {
    "annonce": (
        "Annonce produit ou feature : nouveau modèle, nouvelle fonctionnalité, "
        "lancement officiel d'un acteur de l'IA. Visuel centré sur le nom du produit "
        "et 1 à 2 bénéfices clés."
    ),
    "stat": (
        "Statistique ou benchmark choc : un chiffre frappant, un score de benchmark, "
        "une métrique de performance, un pourcentage d'adoption. Visuel centré sur le chiffre."
    ),
    "citation": (
        "Citation ou déclaration : take provocateur, prédiction, prise de position d'un "
        "dirigeant ou chercheur (Sam Altman, Dario Amodei, Demis Hassabis, etc.). "
        "Visuel éditorial avec quote et attribution."
    ),
    "versus": (
        "Comparaison entre deux entités : Claude vs GPT, OpenAI vs Anthropic, "
        "modèle A vs modèle B. Visuel split-screen ou face-à-face."
    ),
}


# Templates de prompts Gemini par format. Chaque template définit le style visuel,
# les contraintes de design et les instructions précises pour Gemini 3 Pro Image.
PROMPT_TEMPLATES = {
    "annonce": """Crée une infographie carrée 1080x1080 au style éditorial moderne pour annoncer une news IA.

Style visuel :
- Fond sombre (deep navy ou near-black) avec léger grain texturé
- Typographie sans-serif épurée et impactante (style Inter ou similaire)
- Une accent color vive et cohérente avec la marque concernée (orange Anthropic, vert OpenAI, bleu Google, violet Mistral)
- Layout aéré, hiérarchie claire

Contenu à afficher :
- En haut : le nom de la marque/entreprise concernée en petit, en majuscules
- Au centre : le titre de l'annonce en très grand, max 8 mots
- En bas : une courte phrase descriptive (max 12 mots) qui résume le bénéfice

DÉTAILS DE LA NEWS :
Marque : {brand}
Annonce : {announcement}
Bénéfice clé : {benefit}

Le texte affiché doit être PARFAITEMENT lisible, sans fautes d'orthographe, sans caractères corrompus. Pas d'illustration superflue, design minimaliste et premium.""",

    "stat": """Crée une infographie carrée 1080x1080 type "stat card" pour mettre en valeur un chiffre fort.

Style visuel :
- Fond clair (off-white ou cream) ou très sombre selon le contraste optimal
- Le CHIFFRE occupe 50% de l'espace au centre, en très très gros, typo bold ou black weight
- Couleur d'accent vive pour le chiffre uniquement
- Layout grille minimaliste, beaucoup de blanc autour

Contenu à afficher :
- En haut à gauche : un mini label de catégorie (ex : "BENCHMARK", "ADOPTION", "PERFORMANCE")
- Au centre, énorme : le chiffre principal (avec son unité : %, x, M, etc.)
- Sous le chiffre : une phrase de contexte (max 10 mots) qui explique
- En bas à droite : la source en petit (ex : "Anthropic, nov. 2025")

DÉTAILS DE LA STAT :
Catégorie : {category}
Chiffre : {number}
Contexte : {context}
Source : {source}

Le chiffre doit être parfaitement lisible et visuellement impactant. Le texte doit être impeccable, sans faute, sans caractère corrompu.""",

    "citation": """Crée une infographie carrée 1080x1080 type "quote card" éditorial premium.

Style visuel :
- Fond uni élégant (deep navy, dark green, ou off-white) avec une texture subtile
- Un gros guillemet ouvrant (« ou ") en accent color, en haut à gauche
- La citation occupe la majorité de l'espace, en typographie serif élégante (style Tiempos ou Playfair)
- Layout magazine, sophistiqué

Contenu à afficher :
- En haut : un grand guillemet d'ouverture stylisé
- Au centre : la citation entre guillemets, max 25 mots, en typo serif
- En bas : "— [Nom], [Titre/Entreprise]" en plus petit, sans-serif

DÉTAILS DE LA CITATION :
Citation : {quote}
Auteur : {author}
Titre : {author_title}

La citation doit être affichée TEXTUELLEMENT sans modification. Texte parfait, sans faute. Design éditorial premium.""",

    "versus": """Crée une infographie carrée 1080x1080 type "versus" pour comparer deux entités IA.

Style visuel :
- Fond divisé en deux moitiés (verticales ou diagonales), couleurs contrastées par marque
- Un grand "VS" au centre, en typo bold, accent color
- Logos ou noms des deux entités en haut de chaque moitié
- Layout symétrique, dramatique mais lisible

Contenu à afficher :
- Moitié gauche : nom de l'entité A en haut, 2-3 caractéristiques en dessous
- Centre : un grand "VS" stylisé
- Moitié droite : nom de l'entité B en haut, 2-3 caractéristiques en dessous
- En bas : une phrase de contexte (max 12 mots)

DÉTAILS DE LA COMPARAISON :
Entité A : {entity_a}
Caractéristiques A : {features_a}
Entité B : {entity_b}
Caractéristiques B : {features_b}
Contexte : {context}

Texte parfait, sans faute, parfaitement lisible des deux côtés.""",
}


def select_format_and_build_prompts(items: List[NewsItem]) -> List[NewsItem]:
    """Pour chaque news, demande à Claude de choisir le format et de remplir le template."""
    if not items:
        return []

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    formats_text = "\n".join(f"- {name} : {desc}" for name, desc in FORMAT_DESCRIPTIONS.items())

    for item in items:
        prompt = f"""Tu es un directeur artistique pour du contenu social media IA.

Voici une news à transformer en visuel. Tu dois :
1. Choisir le format visuel le plus adapté parmi 4 options
2. Extraire les variables nécessaires pour remplir le template

FORMATS DISPONIBLES :
{formats_text}

NEWS :
Source : {item.source}
Titre : {item.title}
Résumé : {item.summary[:1500]}
Angle éditorial proposé : {item.editorial_angle}

Réponds UNIQUEMENT avec un JSON valide de cette forme (pas de markdown, pas de prose) :

Pour "annonce" :
{{"format": "annonce", "variables": {{"brand": "...", "announcement": "...", "benefit": "..."}}}}

Pour "stat" :
{{"format": "stat", "variables": {{"category": "...", "number": "...", "context": "...", "source": "..."}}}}

Pour "citation" :
{{"format": "citation", "variables": {{"quote": "...", "author": "...", "author_title": "..."}}}}

Pour "versus" :
{{"format": "versus", "variables": {{"entity_a": "...", "features_a": "...", "entity_b": "...", "features_b": "...", "context": "..."}}}}

Règles :
- Choisis "annonce" en fallback si aucun autre ne colle vraiment
- Pour "citation", utilise UNIQUEMENT si tu as une vraie citation textuelle d'une personne identifiable
- Tous les textes doivent être en français, sauf les noms propres et les noms de produits
- Les textes doivent être courts et impactants (respecter les limites mentionnées dans les templates)"""

        t0 = time.perf_counter()
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1000,
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
                context={"step": "format_selection", "news_title": item.title[:60]},
            )
            text = response.content[0].text.strip()

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            data = json.loads(text)
            format_name = data["format"]
            variables = data["variables"]

            if format_name not in PROMPT_TEMPLATES:
                logger.warning(f"Format inconnu '{format_name}', fallback annonce")
                format_name = "annonce"
                variables = {
                    "brand": item.source,
                    "announcement": item.title[:80],
                    "benefit": (item.editorial_angle or item.summary)[:120],
                }

            template = PROMPT_TEMPLATES[format_name]
            try:
                final_prompt = template.format(**variables)
            except KeyError as e:
                logger.warning(f"Variable manquante {e} pour format {format_name}, fallback")
                format_name = "annonce"
                final_prompt = PROMPT_TEMPLATES["annonce"].format(
                    brand=item.source,
                    announcement=item.title[:80],
                    benefit=(item.editorial_angle or item.summary)[:120],
                )

            item.visual_format = format_name
            item.image_prompt = final_prompt
            logger.info(f"Format '{format_name}' choisi pour : {item.title[:60]}")

        except Exception as e:
            log_api_call(
                provider="anthropic",
                model=CLAUDE_MODEL,
                operation="messages.create",
                duration_ms=int((time.perf_counter() - t0) * 1000),
                success=False,
                error=str(e),
                context={"step": "format_selection", "news_title": item.title[:60]},
            )
            logger.error(f"Erreur sélection format pour '{item.title[:60]}' : {e}")
            # Fallback minimal
            item.visual_format = "annonce"
            item.image_prompt = PROMPT_TEMPLATES["annonce"].format(
                brand=item.source,
                announcement=item.title[:80],
                benefit=(item.editorial_angle or item.summary)[:120],
            )

    return items
