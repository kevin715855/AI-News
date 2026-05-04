"""Application configuration for local workflow artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_ARTIFACT_DIR = Path("artifacts")
ARTIFACT_SUBDIRS = (
    "raw",
    "readmes",
    "summaries",
    "localized",
    "exports",
)


@dataclass(frozen=True)
class AppConfig:
    """Filesystem configuration for the digest workflow."""

    artifact_dir: Path = DEFAULT_ARTIFACT_DIR
    artifact_subdirs: tuple[str, ...] = field(default=ARTIFACT_SUBDIRS)

    def ensure_artifact_dirs(self) -> None:
        """Create the artifact root and stage subdirectories."""

        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        for subdir in self.artifact_subdirs:
            (self.artifact_dir / subdir).mkdir(parents=True, exist_ok=True)
