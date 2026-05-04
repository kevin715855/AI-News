"""Core models for repository snapshots and extracted documents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryFile:
    """A single file captured from a repository snapshot."""

    path: str
    content: str

    @property
    def normalized_path(self) -> str:
        return self.path.replace("\\", "/").lower()


@dataclass(frozen=True)
class RepositorySnapshot:
    """In-memory representation of a repository at a point in time."""

    repository: str
    files: tuple[RepositoryFile, ...]

    @classmethod
    def from_files(cls, repository: str, files: list[RepositoryFile]) -> "RepositorySnapshot":
        return cls(repository=repository, files=tuple(files))


@dataclass(frozen=True)
class ExtractedDocument:
    """A normalized section extracted from repository documentation."""

    title: str
    path: str
    content: str
