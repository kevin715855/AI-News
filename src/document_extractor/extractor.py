"""Extract documentation files and metadata from repositories."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


class ExtractionError(Exception):
    """Raised when repository documents cannot be extracted."""


@dataclass(frozen=True)
class DocumentMetadata:
    """Metadata describing one extracted document."""

    path: str
    title: str | None
    format: str
    size_bytes: int
    line_count: int
    word_count: int
    is_readme: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Document:
    """Extracted document content and metadata."""

    metadata: DocumentMetadata
    content: str

    def to_dict(self) -> dict[str, object]:
        return {
            "metadata": self.metadata.to_dict(),
            "content": self.content,
        }


class DocumentExtractor:
    """Find and read common documentation files from a repository."""

    DOCUMENT_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
    IGNORED_DIRS = {".git", ".hg", ".svn", ".tox", ".venv", "node_modules", "__pycache__"}

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path)

    def extract(self) -> list[Document]:
        """Return all supported documentation files in deterministic order."""

        self._validate_repo_path()
        documents = [self._read_document(path) for path in self._iter_document_paths()]
        if not documents:
            raise ExtractionError(f"No supported documents found in {self.repo_path}.")
        return documents

    def extract_readme(self) -> Document:
        """Return the repository README with metadata."""

        self._validate_repo_path()
        for path in self._iter_document_paths():
            if self._is_readme(path):
                return self._read_document(path)
        raise ExtractionError(f"No README document found in {self.repo_path}.")

    def _validate_repo_path(self) -> None:
        if not self.repo_path.exists():
            raise ExtractionError(f"Repository path does not exist: {self.repo_path}")
        if not self.repo_path.is_dir():
            raise ExtractionError(f"Repository path is not a directory: {self.repo_path}")

    def _iter_document_paths(self) -> list[Path]:
        paths: list[Path] = []
        for path in self.repo_path.rglob("*"):
            if not path.is_file():
                continue
            if self._has_ignored_parent(path):
                continue
            if path.suffix.lower() in self.DOCUMENT_EXTENSIONS or self._is_readme(path):
                paths.append(path)
        return sorted(paths, key=lambda candidate: self._sort_key(candidate))

    def _read_document(self, path: Path) -> Document:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ExtractionError(f"Document is not valid UTF-8: {path}") from exc

        relative_path = path.relative_to(self.repo_path).as_posix()
        metadata = DocumentMetadata(
            path=relative_path,
            title=_extract_title(content, path),
            format=path.suffix.lower().lstrip(".") or "text",
            size_bytes=path.stat().st_size,
            line_count=_line_count(content),
            word_count=len(content.split()),
            is_readme=self._is_readme(path),
        )
        return Document(metadata=metadata, content=content)

    def _has_ignored_parent(self, path: Path) -> bool:
        relative_parts = path.relative_to(self.repo_path).parts
        return any(part in self.IGNORED_DIRS for part in relative_parts[:-1])

    def _sort_key(self, path: Path) -> tuple[int, str]:
        return (0 if self._is_readme(path) else 1, path.relative_to(self.repo_path).as_posix())

    @staticmethod
    def _is_readme(path: Path) -> bool:
        return path.name.lower().startswith("readme")


def _extract_title(content: str, path: Path) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
        return stripped
    return path.stem or None


def _line_count(content: str) -> int:
    if not content:
        return 0
    return content.count("\n") + (0 if content.endswith("\n") else 1)
