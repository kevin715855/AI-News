"""Command line entry point for repository summary generation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


SUPPORTED_LANGUAGES = {"vi", "en"}


class SummaryGenerationError(RuntimeError):
    """Raised when a repository summary cannot be generated."""


class SummaryGenerator(Protocol):
    def summarize(self, repo_path: Path, language: str = "vi") -> str:
        """Return a localized repository summary."""


@dataclass(frozen=True)
class RepositorySnapshot:
    name: str
    readme_title: str | None
    description: str | None
    file_count: int
    languages: list[str]


class RepositorySummaryGenerator:
    """Local repository summary generator used when no external generator is wired."""

    language_names = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".kt": "Kotlin",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
    }

    def summarize(self, repo_path: Path, language: str = "vi") -> str:
        if language not in SUPPORTED_LANGUAGES:
            raise SummaryGenerationError(f"Unsupported language: {language}")

        snapshot = self._snapshot(repo_path)
        if language == "en":
            return self._format_english(snapshot)
        return self._format_vietnamese(snapshot)

    def _snapshot(self, repo_path: Path) -> RepositorySnapshot:
        if not repo_path.exists():
            raise SummaryGenerationError(f"Repository path does not exist: {repo_path}")
        if not repo_path.is_dir():
            raise SummaryGenerationError(f"Repository path is not a directory: {repo_path}")

        files = [
            path
            for path in repo_path.rglob("*")
            if path.is_file() and ".git" not in path.parts
        ]
        if not files:
            raise SummaryGenerationError(f"No repository files found in: {repo_path}")

        readme = self._read_readme(repo_path)
        title, description = self._parse_readme(readme)
        languages = self._detect_languages(files)
        return RepositorySnapshot(
            name=repo_path.name,
            readme_title=title,
            description=description,
            file_count=len(files),
            languages=languages,
        )

    def _read_readme(self, repo_path: Path) -> str | None:
        for candidate in repo_path.iterdir():
            if candidate.is_file() and candidate.name.lower().startswith("readme"):
                return candidate.read_text(encoding="utf-8", errors="ignore")
        return None

    def _parse_readme(self, readme: str | None) -> tuple[str | None, str | None]:
        if not readme:
            return None, None

        title = None
        description = None
        for line in readme.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") and title is None:
                title = stripped.lstrip("#").strip()
                continue
            if description is None and not stripped.startswith("#"):
                description = stripped
            if title and description:
                break
        return title, description

    def _detect_languages(self, files: list[Path]) -> list[str]:
        languages = {
            self.language_names[path.suffix.lower()]
            for path in files
            if path.suffix.lower() in self.language_names
        }
        return sorted(languages)

    def _format_vietnamese(self, snapshot: RepositorySnapshot) -> str:
        title = snapshot.readme_title or snapshot.name
        description = snapshot.description or "Chua co mo ta trong README."
        languages = ", ".join(snapshot.languages) if snapshot.languages else "chua xac dinh"
        return "\n".join(
            [
                f"# Tom tat kho luu tru: {title}",
                "",
                f"- Ten repository: {snapshot.name}",
                f"- Mo ta: {description}",
                f"- Ngon ngu/chinh cong nghe phat hien: {languages}",
                f"- So tep duoc phan tich: {snapshot.file_count}",
                "- Ket luan: Repository nay da co du lieu co ban de tao ban tom tat tieng Viet.",
            ]
        )

    def _format_english(self, snapshot: RepositorySnapshot) -> str:
        title = snapshot.readme_title or snapshot.name
        description = snapshot.description or "No README description was found."
        languages = ", ".join(snapshot.languages) if snapshot.languages else "unknown"
        return "\n".join(
            [
                f"# Repository summary: {title}",
                "",
                f"- Repository name: {snapshot.name}",
                f"- Description: {description}",
                f"- Detected languages/technologies: {languages}",
                f"- Files analyzed: {snapshot.file_count}",
                "- Conclusion: This repository has enough local data for a summary.",
            ]
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarize",
        description="Generate localized repository summaries.",
    )
    parser.add_argument(
        "args",
        nargs="+",
        help="Repository path, or 'batch' followed by repository paths.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write summary to a file, or batch summaries to a directory.",
    )
    parser.add_argument(
        "--language",
        default="vi",
        choices=sorted(SUPPORTED_LANGUAGES),
        help="Summary language.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    generator: SummaryGenerator | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    active_generator = generator or RepositorySummaryGenerator()

    if args.args[0] == "batch":
        repo_paths = [Path(raw_path) for raw_path in args.args[1:]]
        if not repo_paths:
            parser.error("batch requires at least one repository path")
        return _summarize_batch(repo_paths, args.output, args.language, active_generator)

    if len(args.args) != 1:
        parser.error("single repository mode accepts exactly one repository path")

    return _summarize_one(Path(args.args[0]), args.output, args.language, active_generator)


def _summarize_one(
    repo_path: Path,
    output: Path | None,
    language: str,
    generator: SummaryGenerator,
) -> int:
    try:
        summary = generator.summarize(repo_path, language=language)
    except Exception as exc:
        print(f"ERROR {repo_path}: {exc}")
        return 1

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(summary + "\n", encoding="utf-8")
    else:
        print(summary)
    return 0


def _summarize_batch(
    repo_paths: list[Path],
    output: Path | None,
    language: str,
    generator: SummaryGenerator,
) -> int:
    failures = 0
    if output:
        output.mkdir(parents=True, exist_ok=True)

    for repo_path in repo_paths:
        try:
            summary = generator.summarize(repo_path, language=language)
        except Exception as exc:
            failures += 1
            print(f"ERROR {repo_path}: {exc}")
            continue

        if output:
            destination = output / f"{repo_path.name}.md"
            destination.write_text(summary + "\n", encoding="utf-8")
        else:
            print(f"== {repo_path} ==")
            print(summary)
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
