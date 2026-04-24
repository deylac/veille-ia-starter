"""Modèles de données partagés dans tout le pipeline."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class NewsItem:
    """Représente une news collectée depuis une source."""

    title: str
    url: str
    source: str  # "Anthropic", "Reddit r/singularity", "TLDR AI", etc.
    summary: str = ""  # Résumé/contenu de la news
    published_at: Optional[datetime] = None
    raw_score: Optional[int] = None  # Pour Reddit : nombre d'upvotes

    # Champs remplis par le pipeline
    viral_score: Optional[int] = None  # 1-10, calculé par Claude
    viral_reason: str = ""  # Justification du score
    visual_format: str = "infographie"  # hardcodé pour le format infographie magazine cyan
    image_prompt: str = ""  # Prompt complet envoyé au modèle d'image
    image_path: str = ""  # Chemin local de l'image générée
    hook_fr: str = ""  # Hook LinkedIn suggéré en français
    editorial_angle: str = ""  # Angle éditorial proposé

    # Direction éditoriale (rempli par editorial_director en phase 3.5)
    editorial_angle_type: str = "analyse_outil"  # analyse_outil | tutoriel | decryptage | impact_business | comparaison | debrief
    editorial_brief: str = ""  # directive courte qui oriente l'enrichissement des 6 blocs
    merged_from_urls: list[str] = field(default_factory=list)  # URLs des news fusionnées si merge

    # Contenu structuré pour l'infographie (rempli par content_enrichment)
    structured_content: Optional[dict[str, Any]] = None
    web_sources: list[str] = field(default_factory=list)  # URLs des sources web utilisées
