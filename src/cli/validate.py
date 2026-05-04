"""CLI command for localized content QA validation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from validator.config import ValidatorConfig
from validator.workflow import QAValidator


README_PATH = Path("README.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="validate")
    parser.add_argument(
        "target",
        metavar="file-path",
        help='File to validate, or "readme" to validate README.md.',
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as CI failures.",
    )
    parser.add_argument(
        "--rules",
        help="Comma-separated rule names to run for file validation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    normalized_argv = _normalize_argv(argv)
    args = parser.parse_args(normalized_argv)

    if args.target == "readme":
        return validate_readme(strict=args.strict)
    return validate_path(Path(args.target), strict=args.strict, rules=args.rules)


def validate_readme(strict: bool = False) -> int:
    """Validate the repository README with the complete rule set."""

    return validate_path(README_PATH, strict=strict, rules=None)


def validate_path(path: Path, strict: bool = False, rules: str | None = None) -> int:
    """Validate a localized content file and return the command exit code."""

    config = ValidatorConfig()
    if rules:
        for rule_name in _parse_rules(rules):
            config.enable_rule(rule_name)

    if not path.exists():
        print(f"Validation report: {path}")
        print("FAIL file-exists")
        print(f"  ERROR {path}: [file-exists] File does not exist.")
        return 1

    validator = QAValidator(config=config, strict=strict)
    report = validator.validate_file(path)
    print(report.format())
    return report.exit_code(strict=strict)


def _normalize_argv(argv: Sequence[str] | None) -> Sequence[str] | None:
    if argv and argv[0] in {"validate", "validate-localized"}:
        return argv[1:]
    return argv


def _parse_rules(raw_rules: str) -> list[str]:
    return [rule.strip() for rule in raw_rules.split(",") if rule.strip()]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

