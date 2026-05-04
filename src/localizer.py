"""README localization workflow."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
from typing import Protocol

from translator import TranslationWrapper

logger = logging.getLogger(__name__)

_README_CANDIDATES = ("README.md", "README.markdown", "README")
_LOCAL_LINK_RE = re.compile(r"!?\[[^\]]*]\((?!https?://|mailto:|#)([^)\s]+)(?:\s+\"[^\"]*\")?\)")


class MarkdownTranslator(Protocol):
    def translate_markdown(self, text: str) -> str:
        """Translate Markdown content."""


@dataclass
class LocalizedResult:
    """Result from a README localization run."""

    source_readme: Path
    output_path: Path
    metadata_path: Path
    vietnamese_content: str
    metadata: dict[str, object]


class LocalizerError(Exception):
    """Raised when README localization cannot complete."""


class READMELocalizer:
    """Localize a repository README into localized/README.vi.md."""

    def __init__(
        self,
        translator: MarkdownTranslator | None = None,
        output_dir: str | Path = "localized",
    ) -> None:
        self.translator = translator or TranslationWrapper()
        self.output_dir = Path(output_dir)

    def localize(self, repo_path: str | Path) -> LocalizedResult:
        """Read a README, translate it to Vietnamese, and write localized output."""

        root = Path(repo_path)
        if not root.exists():
            raise LocalizerError(f"Repository path does not exist: {root}")
        if not root.is_dir():
            raise LocalizerError(f"Repository path is not a directory: {root}")

        source = self._find_readme(root)
        source_content = source.read_text(encoding="utf-8")
        translated_chunks = [
            self.translator.translate_markdown(chunk) for chunk in self._chunk_markdown(source_content)
        ]
        vietnamese_content = "".join(translated_chunks)

        destination_dir = root / self.output_dir
        output_path = destination_dir / "README.vi.md"
        metadata_path = destination_dir / ".meta" / "README.vi.json"
        metadata = self._build_metadata(root, source, source_content, output_path)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(vietnamese_content, encoding="utf-8")
            metadata_path.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            logger.exception("Failed to write localized README output")
            raise LocalizerError(f"Failed to write localized README output: {exc}") from exc

        return LocalizedResult(
            source_readme=source,
            output_path=output_path,
            metadata_path=metadata_path,
            vietnamese_content=vietnamese_content,
            metadata=metadata,
        )

    def _find_readme(self, root: Path) -> Path:
        for name in _README_CANDIDATES:
            candidate = root / name
            if candidate.is_file():
                return candidate

        for candidate in sorted(root.glob("README.*")):
            if candidate.is_file():
                return candidate

        raise LocalizerError(f"No README file found in {root}")

    def _chunk_markdown(self, content: str) -> list[str]:
        if len(content) <= 6000:
            return [content]

        chunks: list[str] = []
        current: list[str] = []
        current_size = 0
        for part in re.split(r"(\n#{1,6} .*)", content):
            if current and current_size + len(part) > 6000:
                chunks.append("".join(current))
                current = []
                current_size = 0
            current.append(part)
            current_size += len(part)
        if current:
            chunks.append("".join(current))
        return chunks

    def _build_metadata(
        self,
        root: Path,
        source: Path,
        source_content: str,
        output_path: Path,
    ) -> dict[str, object]:
        references = sorted(set(_LOCAL_LINK_RE.findall(source_content)))
        return {
            "source_readme": source.relative_to(root).as_posix(),
            "output_readme": output_path.relative_to(root).as_posix(),
            "target_language": "vi",
            "source_file_references": references,
        }


def localize(repo_path: str | Path) -> LocalizedResult:
    """Convenience entry point for README localization."""

    return READMELocalizer().localize(repo_path)
