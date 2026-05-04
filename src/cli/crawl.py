"""CLI for crawling and analyzing local repositories."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from crawler import CrawlError, CrawlResult, LocalRepoCrawler


STATUS_FILE = Path(".crawl-status.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crawl")
    parser.add_argument(
        "repo_path",
        nargs="?",
        help="Local repository path to crawl, or 'status' to show the latest crawl.",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Maximum directory depth to scan from the repository root.",
    )
    parser.add_argument(
        "--include-docs",
        action="store_true",
        help="Include documentation files such as README.md and .rst files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.repo_path == "status":
        return _show_status()
    if not args.repo_path:
        parser.error("repo_path is required unless using 'crawl status'")

    try:
        crawler = LocalRepoCrawler(depth=args.depth, include_docs=args.include_docs)
        result = crawler.crawl(args.repo_path)
    except CrawlError as exc:
        print(f"ERROR {exc}")
        return 1

    status = _status_payload(result, depth=args.depth, include_docs=args.include_docs)
    STATUS_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(_format_result(status))
    return 0


def _show_status() -> int:
    if not STATUS_FILE.exists():
        print("No crawl status found.")
        return 1

    status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    print(_format_result(status))
    return 0


def _status_payload(
    result: CrawlResult, depth: int | None, include_docs: bool
) -> dict[str, object]:
    payload = result.to_dict()
    payload["depth"] = depth
    payload["include_docs"] = include_docs
    payload["completed_at"] = datetime.now(timezone.utc).isoformat()
    return payload


def _format_result(status: dict[str, object]) -> str:
    languages = status.get("languages", {})
    if isinstance(languages, dict) and languages:
        language_summary = ", ".join(f"{name}: {count}" for name, count in languages.items())
    else:
        language_summary = "none"

    return "\n".join(
        [
            f"Crawl status: {status['repo_path']}",
            f"Files analyzed: {status['file_count']}",
            f"Documentation files: {status['documentation_count']}",
            f"Directories scanned: {status['directories_scanned']}",
            f"Total size: {status['total_size_bytes']} bytes",
            f"Languages: {language_summary}",
        ]
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
