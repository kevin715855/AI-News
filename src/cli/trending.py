"""CLI commands for fetching and listing GitHub Trending repositories."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from trending_fetcher import (
    GitHubTrendingFetcher,
    TrendingFetchError,
    TrendingRepository,
    VALID_PERIODS,
    repositories_to_dicts,
)


DEFAULT_CACHE_PATH = (
    Path.home() / ".cache" / "github-trending-vi-digest" / "trending.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trending")
    configure_parser(parser)
    return parser


def configure_parser(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="trending_command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch GitHub Trending repositories.")
    fetch.add_argument("--language", default="", help="Programming language to filter by.")
    fetch.add_argument(
        "--period",
        default="daily",
        choices=sorted(VALID_PERIODS),
        help="Trending period.",
    )
    fetch.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum number of repositories to fetch.",
    )

    subparsers.add_parser("list", help="List the last fetched repositories.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    return run(parser.parse_args(argv))


def run(args: argparse.Namespace) -> int:
    cache_path = _cache_path()
    if args.trending_command == "fetch":
        return fetch_command(
            language=args.language,
            period=args.period,
            limit=args.limit,
            cache_path=cache_path,
        )
    if args.trending_command == "list":
        return list_command(cache_path=cache_path)
    raise ValueError(f"Unknown trending command: {args.trending_command}")


def fetch_command(
    language: str,
    period: str,
    limit: int,
    cache_path: Path = DEFAULT_CACHE_PATH,
    fetcher: GitHubTrendingFetcher | None = None,
) -> int:
    fetcher = fetcher or GitHubTrendingFetcher()
    try:
        repositories = fetcher.fetch(language=language or None, period=period, limit=limit)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except TrendingFetchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _write_cache(cache_path, repositories)
    print(f"Fetched {len(repositories)} repositories.")
    print(_format_repositories(repositories))
    return 0


def list_command(cache_path: Path = DEFAULT_CACHE_PATH) -> int:
    try:
        repositories = _read_cache(cache_path)
    except FileNotFoundError:
        print("No fetched repositories found. Run `trending fetch` first.")
        return 1
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"Error: unable to read cached repositories: {exc}", file=sys.stderr)
        return 1

    print(_format_repositories(repositories))
    return 0


def _cache_path() -> Path:
    override = os.environ.get("GITHUB_TRENDING_CACHE")
    return Path(override) if override else DEFAULT_CACHE_PATH


def _write_cache(cache_path: Path, repositories: list[TrendingRepository]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = repositories_to_dicts(repositories)
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_cache(cache_path: Path) -> list[TrendingRepository]:
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("cache root must be a list")
    return [TrendingRepository.from_dict(item) for item in payload]


def _format_repositories(repositories: list[TrendingRepository]) -> str:
    if not repositories:
        return "No repositories found."

    rows = [
        (
            str(index),
            repository.full_name,
            repository.language or "-",
            str(repository.stars),
            str(repository.stars_in_period),
            repository.description or "-",
        )
        for index, repository in enumerate(repositories, start=1)
    ]
    headers = ("#", "Repository", "Language", "Stars", "Period", "Description")
    widths = [
        max(len(row[column]) for row in (headers, *rows))
        for column in range(len(headers))
    ]
    lines = [_format_row(headers, widths), _format_row(tuple("-" * width for width in widths), widths)]
    lines.extend(_format_row(row, widths) for row in rows)
    return "\n".join(lines)


def _format_row(row: tuple[str, ...], widths: list[int]) -> str:
    return "  ".join(value.ljust(width) for value, width in zip(row, widths))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
