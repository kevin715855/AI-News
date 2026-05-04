"""Extraction logic for selecting useful repository documentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
import re

from .core import ExtractedDocument, RepositoryFile, RepositorySnapshot

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_DOCUMENT_EXTENSIONS = {".md", ".mdx", ".rst", ".txt"}
_PREFERRED_FILENAMES = {
    "readme.md",
    "contributing.md",
    "changelog.md",
    "architecture.md",
    "design.md",
}


@dataclass(frozen=True)
class DocumentExtractorConfig:
    """Runtime limits and filters for extraction."""

    max_documents: int = 12
    max_characters_per_document: int = 3500
    min_characters: int = 40
    document_extensions: set[str] = field(
        default_factory=lambda: set(_DOCUMENT_EXTENSIONS)
    )

    def __post_init__(self) -> None:
        if self.max_documents <= 0:
            raise ValueError("max_documents must be greater than zero.")
        if self.max_characters_per_document <= 0:
            raise ValueError("max_characters_per_document must be greater than zero.")
        if self.min_characters < 0:
            raise ValueError("min_characters cannot be negative.")


class DocumentExtractor:
    """Extracts ranked documentation sections from a repository snapshot."""

    def __init__(self, config: DocumentExtractorConfig | None = None) -> None:
        self.config = config or DocumentExtractorConfig()

    def extract(self, snapshot: RepositorySnapshot) -> list[ExtractedDocument]:
        ranked_candidates = sorted(
            (item for item in snapshot.files if self._is_candidate(item)),
            key=self._rank_key,
            reverse=True,
        )

        extracted: list[ExtractedDocument] = []
        for file in ranked_candidates:
            normalized_text = _normalize_text(file.content)
            if len(normalized_text) < self.config.min_characters:
                continue

            for title, section_text in _split_markdown_sections(normalized_text):
                if len(extracted) >= self.config.max_documents:
                    return extracted
                if len(section_text) < self.config.min_characters:
                    continue

                extracted.append(
                    ExtractedDocument(
                        title=title or _title_from_path(file.path),
                        path=file.path,
                        content=_truncate(
                            section_text,
                            self.config.max_characters_per_document,
                        ),
                    )
                )

        return extracted

    def _is_candidate(self, file: RepositoryFile) -> bool:
        normalized_path = file.normalized_path
        if _looks_binary(file.content):
            return False
        path = PurePosixPath(normalized_path)
        filename = path.name

        if filename in {"license", "copying"}:
            return True
        if filename in _PREFERRED_FILENAMES:
            return True
        return path.suffix in self.config.document_extensions

    def _rank_key(self, file: RepositoryFile) -> tuple[int, int]:
        path = PurePosixPath(file.normalized_path)
        filename = path.name
        score = 0

        if filename.startswith("readme"):
            score += 300
        if "/docs/" in f"/{file.normalized_path}/":
            score += 200
        if filename in _PREFERRED_FILENAMES:
            score += 150
        if path.suffix == ".md":
            score += 80
        score -= len(path.parts)

        return (score, -len(file.content))


def extract_documents(
    snapshot: RepositorySnapshot,
    *,
    max_documents: int = 12,
    max_characters_per_document: int = 3500,
) -> list[ExtractedDocument]:
    """Convenience API for one-off extraction."""

    config = DocumentExtractorConfig(
        max_documents=max_documents,
        max_characters_per_document=max_characters_per_document,
    )
    return DocumentExtractor(config).extract(snapshot)


def _normalize_text(content: str) -> str:
    lines = [line.rstrip() for line in content.replace("\r\n", "\n").split("\n")]
    compact_lines = [line for line in lines]
    normalized = "\n".join(compact_lines).strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


def _split_markdown_sections(content: str) -> list[tuple[str | None, str]]:
    lines = content.splitlines()
    if not lines:
        return []

    sections: list[tuple[str | None, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            if current_lines:
                section_text = "\n".join(current_lines).strip()
                if section_text:
                    sections.append((current_title, section_text))
            current_title = heading_match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        section_text = "\n".join(current_lines).strip()
        if section_text:
            sections.append((current_title, section_text))

    return sections


def _title_from_path(path: str) -> str:
    stem = PurePosixPath(path.replace("\\", "/")).stem
    cleaned = stem.replace("-", " ").replace("_", " ").strip()
    return cleaned.title() if cleaned else "Untitled"


def _truncate(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content
    if max_chars <= 1:
        return content[:max_chars]
    return f"{content[: max_chars - 1]}…"


def _looks_binary(content: str) -> bool:
    return "\x00" in content
