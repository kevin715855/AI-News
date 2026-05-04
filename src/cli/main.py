"""Main command line entry point for github-trending-vi-digest."""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence

from .config import CLIConfig

COMMANDS = (
    ("trending", "Fetch GitHub Trending repository metadata."),
    ("crawl", "Crawl repository pages and README content."),
    ("extract", "Extract structured facts from crawled content."),
    ("summarize", "Generate digest summaries."),
    ("localize", "Localize digest content for Vietnamese readers."),
    ("validate", "Validate generated localized output."),
    ("export", "Export the final digest."),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="github-trending-vi-digest",
        description="Produce Vietnamese digests of GitHub Trending repositories.",
    )
    _add_global_options(parser)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
        help="Show version information and exit.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)
    for command_name, help_text in COMMANDS:
        command_parser = subparsers.add_parser(
            command_name,
            help=help_text,
            description=help_text,
        )
        _add_global_options(command_parser)
        command_parser.set_defaults(handler=_run_placeholder_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if argv and argv[0] == "trending" and len(argv) > 1:
        from .trending import main as trending_main

        return trending_main(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = CLIConfig.load(
            config_path=getattr(args, "config", None),
            output_dir=getattr(args, "output_dir", None),
            verbose=getattr(args, "verbose", False),
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
        return 2

    return handler(args, config)


def get_version() -> str:
    try:
        return version("github-trending-vi-digest")
    except PackageNotFoundError:
        return "0.1.0"


def _add_global_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=argparse.SUPPRESS,
        help="Path to a JSON configuration file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=argparse.SUPPRESS,
        help="Directory for generated output.",
    )


def _run_placeholder_command(args: argparse.Namespace, config: CLIConfig) -> int:
    if config.verbose:
        print(f"Config: output_dir={config.output_dir}")
    print(f"{args.command}: command group is ready.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
