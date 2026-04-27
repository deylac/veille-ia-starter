"""Collecteur d'événements du run quotidien.

Instancié au début de main.py, passé aux phases qui ont des stats à reporter
(scoring, éditorial). Persisté en fin de run dans la table Supabase `daily_runs`,
puis lu par publish/notion_daily_report.py pour publier le rapport Notion.

API minimaliste : un objet, des setters, un to_dict() pour Supabase.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from config.settings import TZ


@dataclass
class RunReport:
    start_time: datetime = field(default_factory=lambda: datetime.now(TZ))
    end_time: datetime | None = None

    # Phase 1 : collecte
    total_collected: int = 0
    by_source: dict[str, int] = field(default_factory=dict)

    # Phase 3 : scoring (TOUTES les news scorées, retenues ou non)
    scoring: list[dict[str, Any]] = field(default_factory=list)
    # Format : { "title": str, "source": str, "score": int, "reason": str, "kept": bool }

    # Phase 3.5 : éditorial
    editorial: dict[str, Any] = field(default_factory=dict)
    # Format : { "selected_count": int, "rejected_indices": [int], "reasoning": str }

    # Phases 4-7 : compteurs simples
    enriched_count: int = 0
    published_count: int = 0
    carousel_slides_count: int = 0

    # Si le pipeline s'arrête tôt
    early_exit_reason: str | None = None

    # Coût (rempli en fin de run depuis api_calls)
    cost_usd: float = 0.0

    def add_collected(self, source: str, count: int) -> None:
        self.by_source[source] = self.by_source.get(source, 0) + count
        self.total_collected += count

    def set_scoring(self, scores: list[dict[str, Any]]) -> None:
        self.scoring = scores

    def set_editorial(self, decision: dict[str, Any]) -> None:
        self.editorial = decision

    def set_enriched(self, n: int) -> None:
        self.enriched_count = n

    def set_published(self, n: int) -> None:
        self.published_count = n

    def set_carousel(self, n: int) -> None:
        self.carousel_slides_count = n

    def set_early_exit(self, reason: str) -> None:
        self.early_exit_reason = reason

    def finalize(self) -> None:
        self.end_time = datetime.now(TZ)

    @property
    def duration_seconds(self) -> int:
        end = self.end_time or datetime.now(TZ)
        return int((end - self.start_time).total_seconds())

    def to_db_row(self) -> dict[str, Any]:
        """Sérialise en dict prêt pour upsert dans la table Supabase daily_runs."""
        return {
            "date": self.start_time.date().isoformat(),
            "ran_at": self.start_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "total_collected": self.total_collected,
            "by_source": self.by_source,
            "scoring": self.scoring,
            "editorial": self.editorial,
            "enriched_count": self.enriched_count,
            "published_count": self.published_count,
            "carousel_slides_count": self.carousel_slides_count,
            "cost_usd": round(self.cost_usd, 4),
            "early_exit_reason": self.early_exit_reason,
        }
