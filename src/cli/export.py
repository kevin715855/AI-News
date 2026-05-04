"""CLI commands for exporting repository summaries."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from exporter import ExportData, ExporterConfig, JSONExporter, MarkdownExporter


class ExportError(Exception):
    """Raised when export input cannot be loaded."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="digest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export", help="Export repository summaries.")
    export_subparsers = export.add_subparsers(dest="export_format", required=True)

    markdown = export_subparsers.add_parser("markdown", help="Export Markdown.")
    _add_common_export_args(markdown)
    markdown.add_argument("--output", required=True, type=Path)

    json_parser = export_subparsers.add_parser("json", help="Export JSON.")
    _add_common_export_args(json_parser)
    json_parser.add_argument("--output", required=True, type=Path)

    all_parser = export_subparsers.add_parser("all", help="Export all formats.")
    _add_common_export_args(all_parser)
    all_parser.add_argument("--output-dir", required=True, type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "export":
        parser.error(f"Unknown command: {args.command}")
        return 1

    try:
        data = load_export_data(args.repo_path)
        config = ExporterConfig(
            include_readme=args.include_readme,
            pretty=args.pretty,
            indent=args.indent,
        )
        if args.export_format == "markdown":
            MarkdownExporter(config).export(data, args.output)
        elif args.export_format == "json":
            JSONExporter(config).export(data, args.output)
        elif args.export_format == "all":
            args.output_dir.mkdir(parents=True, exist_ok=True)
            MarkdownExporter(config).export(data, args.output_dir / f"{data.repo_name}.md")
            JSONExporter(config).export(data, args.output_dir / f"{data.repo_name}.json")
        else:
            parser.error(f"Unknown export format: {args.export_format}")
            return 1
    except ExportError as exc:
        if str(exc).startswith("Repository path does not exist"):
            parser.error(str(exc))
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 1

    return 0


def load_export_data(repo_path: str | Path) -> ExportData:
    path = Path(repo_path)
    if not path.exists():
        raise ExportError(f"Repository path does not exist: {path}")

    data_path = path / "export-data.json"
    if not data_path.exists():
        return build_export_data(path)

    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExportError(f"Invalid export data JSON: {data_path}") from exc

    try:
        return ExportData(
            repo_name=payload["repo_name"],
            repo_url=payload["repo_url"],
            summary=payload["summary"],
            readme_content=payload.get("readme_content"),
            metadata=payload.get("metadata", {}),
            description=payload.get("description") or payload.get("metadata", {}).get("description"),
            source_files=payload.get("source_files", []),
        )
    except KeyError as exc:
        raise ExportError(f"Missing required export field: {exc.args[0]}") from exc


def export_markdown(repo_path: str | Path, output_path: str | Path, include_readme: bool = True) -> Path:
    path = Path(output_path)
    MarkdownExporter(ExporterConfig(include_readme=include_readme)).export(load_export_data(repo_path), path)
    return path


def export_json(
    repo_path: str | Path,
    output_path: str | Path,
    include_readme: bool = True,
    pretty: bool = True,
) -> Path:
    path = Path(output_path)
    JSONExporter(ExporterConfig(include_readme=include_readme, pretty=pretty)).export(load_export_data(repo_path), path)
    return path


def export_all(
    repo_path: str | Path,
    output_dir: str | Path,
    include_readme: bool = True,
    pretty: bool = True,
) -> tuple[Path, Path]:
    data = load_export_data(repo_path)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    markdown_path = directory / f"{data.repo_name}.md"
    json_path = directory / f"{data.repo_name}.json"
    MarkdownExporter(ExporterConfig(include_readme=include_readme)).export(data, markdown_path)
    JSONExporter(ExporterConfig(include_readme=include_readme, pretty=pretty)).export(data, json_path)
    return markdown_path, json_path


def build_export_data(repo_path: Path, include_readme: bool = True) -> ExportData:
    repo_path = repo_path.resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise ExportError(f"Repository path does not exist: {repo_path}")

    readme_path = _find_readme(repo_path)
    readme_content = readme_path.read_text(encoding="utf-8") if readme_path and include_readme else None
    summary = _read_optional_text(repo_path, ["SUMMARY.md", "summary.md", "digest_summary.md"])
    if not summary:
        summary = _summary_from_readme(readme_content) if readme_content else "Chua co tom tat tieng Viet."

    source_files = [str(path.relative_to(repo_path)) for path in sorted(repo_path.rglob("*")) if path.is_file()]
    metadata = {
        "language": _detect_primary_language(source_files),
        "file_count": len(source_files),
        "updated_at": datetime.fromtimestamp(repo_path.stat().st_mtime, tz=timezone.utc).isoformat(),
    }
    if readme_path:
        metadata["readme"] = str(readme_path.relative_to(repo_path))

    return ExportData(
        repo_name=repo_path.name,
        repo_url=_read_git_remote(repo_path) or "",
        summary=summary,
        readme_content=readme_content,
        metadata=metadata,
        description=_first_heading(readme_content),
        source_files=source_files,
    )


def _add_common_export_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("repo_path", type=Path)
    parser.add_argument(
        "--include-readme",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include localized README content in export output.",
    )
    parser.add_argument(
        "--pretty",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pretty-print structured output.",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation size.")


def _find_readme(repo_path: Path) -> Path | None:
    for name in ("README.vi.md", "README.md", "readme.md"):
        path = repo_path / name
        if path.exists():
            return path
    return None


def _read_optional_text(repo_path: Path, names: list[str]) -> str | None:
    for name in names:
        path = repo_path / name
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return None


def _summary_from_readme(readme_content: str | None) -> str:
    if not readme_content:
        return "Chua co tom tat tieng Viet."
    paragraphs = [block.strip() for block in readme_content.split("\n\n") if block.strip()]
    return paragraphs[1] if len(paragraphs) > 1 else paragraphs[0]


def _first_heading(readme_content: str | None) -> str | None:
    if not readme_content:
        return None
    for line in readme_content.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return None


def _detect_primary_language(source_files: list[str]) -> str:
    extension_counts: dict[str, int] = {}
    for file_name in source_files:
        suffix = Path(file_name).suffix.lower()
        if suffix:
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
    if not extension_counts:
        return "unknown"
    preferred_suffixes = [".py", ".ts", ".js", ".go", ".rs", ".java", ".md"]
    suffix = max(
        extension_counts,
        key=lambda item: (
            extension_counts[item],
            -preferred_suffixes.index(item) if item in preferred_suffixes else -len(preferred_suffixes),
        ),
    )
    return {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".md": "Markdown",
        ".go": "Go",
        ".rs": "Rust",
    }.get(suffix, suffix.lstrip("."))


def _read_git_remote(repo_path: Path) -> str | None:
    config_path = repo_path / ".git" / "config"
    if not config_path.exists():
        return None
    current_remote = None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[remote "):
            current_remote = stripped
            continue
        if current_remote and stripped.startswith("url = "):
            return stripped.removeprefix("url = ").strip()
    return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
