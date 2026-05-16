"""Command line entry point for the full digest workflow."""

from __future__ import annotations

import argparse
import sys

from pathlib import Path
from typing import Sequence

from .ai import LMStudioConfig, LMStudioProvider
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
    parser.add_argument(
        "--lmstudio-base-url",
        default="http://127.0.0.1:1234/v1",
        help="OpenAI-compatible LM Studio API base URL.",
    )
    parser.add_argument(
        "--model",
        default="local-model",
        help="Model name loaded in LM Studio.",
    )
    parser.add_argument(
        "--ai-timeout",
        type=float,
        default=60.0,
        help="AI request timeout in seconds.",
    )
    parser.add_argument(
        "--ai-retries",
        type=int,
        default=1,
        help="Number of retry attempts for transient AI failures.",
    )
    parser.add_argument(
        "--ai-max-tokens",
        type=int,
        default=1400,
        help="Maximum output tokens requested from the local model.",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Run the full workflow.")
    repo_parser = subparsers.add_parser("repo", help="Run a digest for one GitHub repository URL.")
    repo_parser.add_argument("url", help="GitHub repository URL.")
    subparsers.add_parser("fetch", help="Fetch trending repositories.")
    subparsers.add_parser("clone", help="Clone repositories from saved fetch state.")
    subparsers.add_parser("analyze", help="Analyze cloned README/docs.")
    subparsers.add_parser("summarize", help="Generate Vietnamese summaries.")
    subparsers.add_parser("localize", help="Create localized README files.")
    subparsers.add_parser("validate", help="Validate localized README files.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
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
        ai_provider=LMStudioProvider(
            LMStudioConfig(
                base_url=args.lmstudio_base_url,
                model=args.model,
                timeout_seconds=args.ai_timeout,
                retries=args.ai_retries,
                max_tokens=args.ai_max_tokens,
            )
        ),
        progress=lambda message: print(f"[digest] {message}"),
    )

    try:
        if command == "run":
            workflow.run()
        elif command == "repo":
            repos = workflow.prepare_repository_url(args.url)
            workflow.clone_repositories(repos)
            analyses = workflow.analyze_repositories(repos)
            workflow.generate_markdown_outputs(analyses)
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
