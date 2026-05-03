"""Command line entry point for localized README QA validation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .config import ValidatorConfig
from .workflow import QAValidator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="validator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate-localized",
        help="Validate a localized README file.",
    )
    validate.add_argument("readme_path", type=Path)
    validate.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as CI failures.",
    )
    validate.add_argument(
        "--rules",
        help="Comma-separated rule names to run.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if argv and argv[0] != "validate-localized":
        return _validate_localized_entry(argv)

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-localized":
        return _validate_localized(args.readme_path, args.strict, args.rules)

    parser.error(f"Unknown command: {args.command}")
    return 1


def validate_localized_main(argv: Sequence[str] | None = None) -> int:
    return _validate_localized_entry(argv)


def _validate_localized_entry(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-localized")
    parser.add_argument("readme_path", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as CI failures.",
    )
    parser.add_argument(
        "--rules",
        help="Comma-separated rule names to run.",
    )
    args = parser.parse_args(argv)
    return _validate_localized(args.readme_path, args.strict, args.rules)


def _validate_localized(readme_path: Path, strict: bool, rules: str | None) -> int:
    config = ValidatorConfig()
    if rules:
        for rule_name in _parse_rules(rules):
            config.enable_rule(rule_name)

    if not readme_path.exists():
        print(f"Validation report: {readme_path}")
        print(f"FAIL file-exists")
        print(f"  ERROR {readme_path}: [file-exists] File does not exist.")
        return 1

    validator = QAValidator(config=config, strict=strict)
    report = validator.validate_file(readme_path)
    print(report.format())
    return report.exit_code(strict=strict)


def _parse_rules(raw_rules: str) -> list[str]:
    return [rule.strip() for rule in raw_rules.split(",") if rule.strip()]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
