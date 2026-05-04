"""Command line interface for extracting repository documents."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence

from document_extractor import Document, DocumentExtractor, ExtractionError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="extract")
    parser.add_argument("repo_path", type=Path, help="Repository path to scan.")
    _add_output_options(parser)
    return parser


def build_readme_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="extract readme")
    parser.add_argument("repo_path", type=Path, help="Repository path containing a README.")
    _add_output_options(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv if argv is not None else sys.argv[1:])
    readme_only = args_list[:1] == ["readme"]
    parser = build_readme_parser() if readme_only else build_parser()
    if readme_only:
        args_list = args_list[1:]

    args = parser.parse_args(args_list)
    extractor = DocumentExtractor(args.repo_path)

    try:
        documents = [extractor.extract_readme()] if readme_only else extractor.extract()
        output = _format_output(args.repo_path, documents, args.format)
        if args.output_dir:
            destination = _write_output(
                args.output_dir,
                documents,
                args.format,
                repo_path=args.repo_path,
                readme_only=readme_only,
            )
            print(f"Wrote extracted documents to {destination}")
        else:
            print(output)
        return 0
    except ExtractionError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where extracted output should be written.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format.",
    )


def _format_output(repo_path: Path, documents: list[Document], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(
            {
                "repo_path": str(repo_path),
                "document_count": len(documents),
                "documents": [document.to_dict() for document in documents],
            },
            indent=2,
            sort_keys=True,
        )

    lines = [f"Repository: {repo_path}", f"Documents: {len(documents)}"]
    for document in documents:
        metadata = document.metadata
        title = f" - {metadata.title}" if metadata.title else ""
        lines.append(
            f"{metadata.path}{title} "
            f"({metadata.format}, {metadata.line_count} lines, {metadata.word_count} words)"
        )
    return "\n".join(lines)


def _write_output(
    output_dir: Path,
    documents: list[Document],
    output_format: str,
    *,
    repo_path: Path,
    readme_only: bool,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        destination = output_dir / ("readme.json" if readme_only else "documents.json")
        destination.write_text(
            _format_output(repo_path, documents, "json"),
            encoding="utf-8",
        )
        return destination

    for document in documents:
        destination = output_dir / f"{_safe_output_name(document.metadata.path)}.txt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(_format_text_document(document), encoding="utf-8")
    return output_dir


def _format_text_document(document: Document) -> str:
    metadata = document.metadata
    header = [
        f"Path: {metadata.path}",
        f"Title: {metadata.title or ''}",
        f"Format: {metadata.format}",
        f"Lines: {metadata.line_count}",
        f"Words: {metadata.word_count}",
        "",
    ]
    return "\n".join(header) + document.content


def _safe_output_name(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path).strip("_") or "document"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
