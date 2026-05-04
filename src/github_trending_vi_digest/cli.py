"""Command line entry point for the digest workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .config import AppConfig


WORKFLOW_COMMANDS = (
    "fetch",
    "crawl",
    "extract",
    "summarize",
    "localize",
    "export",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="github-trending-vi-digest",
        description="Produce Vietnamese digests of GitHub Trending repositories.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=AppConfig().artifact_dir,
        help="Directory used for generated workflow artifacts.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Create the local artifact directory layout.")

    for command in WORKFLOW_COMMANDS:
        subparsers.add_parser(command, help=f"Placeholder for the {command} stage.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AppConfig(artifact_dir=args.artifact_dir)

    if args.command == "init":
        config.ensure_artifact_dirs()
        print(f"Initialized artifact directory: {config.artifact_dir}")
        return 0

    if args.command in WORKFLOW_COMMANDS:
        print(f"{args.command} is not implemented yet.")
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
