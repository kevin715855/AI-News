"""Core data objects passed between digest workflow stages."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RepositoryCandidate:
    """A GitHub repository selected for digest processing."""

    owner: str
    name: str
    url: str
    description: str | None = None
    language: str | None = None
    stars: int | None = None
    topics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class DigestItem:
    """Localized digest content for one repository."""

    repository: RepositoryCandidate
    summary_vi: str
    highlights_vi: tuple[str, ...] = field(default_factory=tuple)
    source_readme_url: str | None = None
