"""Modèles de données pour l'application bibliographique."""

from dataclasses import dataclass, field, asdict
import json


@dataclass
class Article:
    title: str
    authors: list[str] = field(default_factory=list)
    doi: str | None = None
    journal: str | None = None
    year: int | None = None
    abstract: str | None = None
    keywords: list[str] = field(default_factory=list)
    citation_count: int = 0
    source: str = ""

    def completeness_score(self) -> int:
        """Score de complétude pour la déduplication (plus élevé = plus complet)."""
        score = 0
        if self.doi:
            score += 2
        if self.abstract:
            score += 3
        if self.authors:
            score += len(self.authors)
        if self.journal:
            score += 1
        if self.year:
            score += 1
        if self.keywords:
            score += len(self.keywords)
        if self.citation_count > 0:
            score += 1
        return score

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CollectionReport:
    total_collected: int = 0
    per_source: dict[str, int] = field(default_factory=dict)
    duplicates_removed: int = 0
    duplicate_log: list[str] = field(default_factory=list)
    final_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VerificationResult:
    claim: str = ""
    verified: bool = True
    correction: str | None = None
    source: str | None = None
    confidence: float = 0.0


@dataclass
class EditorReport:
    confidence_score: float = 0.0
    verifications: list[VerificationResult] = field(default_factory=list)
    figures_generated: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "confidence_score": self.confidence_score,
            "verifications": [asdict(v) for v in self.verifications],
            "figures_generated": self.figures_generated,
        }


def articles_to_json(articles: list[Article]) -> str:
    return json.dumps([a.to_dict() for a in articles], ensure_ascii=False, indent=2)


def articles_from_json(data: str) -> list[Article]:
    items = json.loads(data)
    return [Article(**item) for item in items]
