"""Command line entry point for the full digest workflow."""

from __future__ import annotations

import argparse

from pathlib import Path
from typing import Sequence

from .workflow import DigestWorkflow, WorkflowError, WorkflowOptions


VALID_PERIODS = ("daily", "weekly", "monthly")
VALID_MODES = ("summarize", "localize", "both")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="github-trending-vi-digest")
    parser.add_argument(
        "--language",
        default="python",
        help="GitHub Trending language filter.",
    )
    parser.add_argument(
        "--period",
        default="daily",
        choices=VALID_PERIODS,
        help="Trending period to fetch.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of repositories to process.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist/digest"),
        help="Directory for clones, state, and generated artifacts.",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="both",
        help="Generate summaries, localized READMEs, or both.",
    )
    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="Treat localized README validation warnings as failures.",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Run the full workflow.")
    subparsers.add_parser("fetch", help="Fetch trending repositories.")
    subparsers.add_parser("clone", help="Clone repositories from saved fetch state.")
    subparsers.add_parser("analyze", help="Analyze cloned README/docs.")
    subparsers.add_parser("summarize", help="Generate Vietnamese summaries.")
    subparsers.add_parser("localize", help="Create localized README files.")
    subparsers.add_parser("validate", help="Validate localized README files.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be greater than zero")

    command = args.command or "run"
    workflow = DigestWorkflow(
        WorkflowOptions(
            language=args.language,
            period=args.period,
            limit=args.limit,
            output_dir=args.output_dir,
            mode=args.mode,
            strict_validation=args.strict_validation,
        ),
        progress=lambda message: print(f"[digest] {message}"),
    )

    try:
        if command == "run":
            workflow.run()
        elif command == "fetch":
            workflow.fetch_trending()
        elif command == "clone":
            workflow.clone_repositories()
        elif command == "analyze":
            workflow.analyze_repositories()
        elif command == "summarize":
            workflow.generate_summaries()
        elif command == "localize":
            workflow.localize_readmes()
        elif command == "validate":
            workflow.validate_outputs()
        else:
            parser.error(f"Unknown command: {command}")
    except WorkflowError as exc:
        print(f"[digest] ERROR {exc}")
        return 1

    print(f"[digest] Done. Output: {workflow.output_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
