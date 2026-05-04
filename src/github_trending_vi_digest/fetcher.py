"""GitHub Trending repository discovery stage."""

from __future__ import annotations

from .models import RepositoryCandidate


def fetch_trending_repositories() -> list[RepositoryCandidate]:
    raise NotImplementedError("GitHub Trending fetcher is not implemented yet.")
