"""Repository README crawling stage."""

from __future__ import annotations

from .models import RepositoryCandidate


def crawl_repository_readme(repository: RepositoryCandidate) -> str:
    raise NotImplementedError("Repository README crawler is not implemented yet.")
