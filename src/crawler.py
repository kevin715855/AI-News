"""Local repository crawler for lightweight source inventory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


DOC_EXTENSIONS = {".adoc", ".markdown", ".md", ".rst", ".txt"}
IGNORED_DIRECTORIES = {".git", ".hg", ".mypy_cache", ".pytest_cache", "__pycache__"}
LANGUAGE_BY_EXTENSION = {
    ".css": "CSS",
    ".go": "Go",
    ".html": "HTML",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".json": "JSON",
    ".md": "Markdown",
    ".py": "Python",
    ".rs": "Rust",
    ".sh": "Shell",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".yaml": "YAML",
    ".yml": "YAML",
}


@dataclass(frozen=True)
class CrawledFile:
    """Metadata captured for one repository file."""

    path: str
    size_bytes: int
    language: str
    is_documentation: bool


@dataclass
class CrawlResult:
    """Aggregate crawl output for a repository."""

    repo_path: Path
    files: list[CrawledFile] = field(default_factory=list)
    directories_scanned: int = 0

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def documentation_count(self) -> int:
        return sum(1 for file in self.files if file.is_documentation)

    @property
    def total_size_bytes(self) -> int:
        return sum(file.size_bytes for file in self.files)

    @property
    def languages(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for file in self.files:
            counts[file.language] = counts.get(file.language, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_path": str(self.repo_path),
            "file_count": self.file_count,
            "documentation_count": self.documentation_count,
            "directories_scanned": self.directories_scanned,
            "total_size_bytes": self.total_size_bytes,
            "languages": self.languages,
            "files": [file.__dict__ for file in self.files],
        }


class CrawlError(ValueError):
    """Raised when a repository cannot be crawled."""


class LocalRepoCrawler:
    """Crawl a local git repository and summarize source files."""

    def __init__(self, depth: int | None = None, include_docs: bool = False) -> None:
        if depth is not None and depth < 0:
            raise CrawlError("--depth must be zero or greater")
        self.depth = depth
        self.include_docs = include_docs

    def crawl(self, repo_path: str | Path) -> CrawlResult:
        root = Path(repo_path).expanduser().resolve()
        self._validate_repo(root)

        result = CrawlResult(repo_path=root)
        for directory in self._walk_directories(root):
            result.directories_scanned += 1
            for file_path in sorted(path for path in directory.iterdir() if path.is_file()):
                crawled = self._crawl_file(root, file_path)
                if crawled.is_documentation and not self.include_docs:
                    continue
                result.files.append(crawled)
        return result

    def _validate_repo(self, root: Path) -> None:
        if not root.exists():
            raise CrawlError(f"Repository path does not exist: {root}")
        if not root.is_dir():
            raise CrawlError(f"Repository path is not a directory: {root}")
        if not (root / ".git").exists():
            raise CrawlError(f"Missing git repository metadata: {root}")

    def _walk_directories(self, root: Path) -> Iterable[Path]:
        pending = [root]
        while pending:
            directory = pending.pop(0)
            yield directory

            children = sorted(
                path
                for path in directory.iterdir()
                if path.is_dir() and path.name not in IGNORED_DIRECTORIES
            )
            for child in children:
                if self._within_depth(root, child):
                    pending.append(child)

    def _within_depth(self, root: Path, path: Path) -> bool:
        if self.depth is None:
            return True
        return len(path.relative_to(root).parts) <= self.depth

    def _crawl_file(self, root: Path, file_path: Path) -> CrawledFile:
        extension = file_path.suffix.lower()
        return CrawledFile(
            path=file_path.relative_to(root).as_posix(),
            size_bytes=file_path.stat().st_size,
            language=LANGUAGE_BY_EXTENSION.get(extension, "Other"),
            is_documentation=extension in DOC_EXTENSIONS,
        )
