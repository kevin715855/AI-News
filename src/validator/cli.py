"""Command line entry point for localized README QA validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import ValidatorConfig
from .trending import TrendingFetcher
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
    if argv and argv[0] == "export":
        from cli.export import main as export_main

        try:
            exit_code = export_main(argv)
        except SystemExit:
            return 1
        if exit_code == 0:
            _normalize_legacy_json_exports(argv)
        return exit_code

    if argv and argv[0] == "fetch":
        return _fetch_main(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-localized":
        return _validate_localized(args.readme_path, args.strict, args.rules)

    parser.error(f"Unknown command: {args.command}")
    return 1


def validate_localized_main(argv: Sequence[str] | None = None) -> int:
    """Console-script wrapper for validating a localized README path."""

    return _validate_localized_args(argv)


def _validate_localized_args(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-localized")
    parser.add_argument("readme_path", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--rules")
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


def _fetch_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validator fetch")
    parser.add_argument("--language")
    parser.add_argument("--since", default="daily")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output-file", type=Path, default=Path("trending.json"))
    args = parser.parse_args(argv)

    try:
        repositories = TrendingFetcher().fetch(args.language, args.since, args.limit)
    except Exception as exc:
        print(f"Fetch failed: {exc}")
        return 1

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = [repository.to_dict() for repository in repositories]
    args.output_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(repositories)} repositories to {args.output_file}")
    return 0


def _normalize_legacy_json_exports(argv: Sequence[str]) -> None:
    if len(argv) < 3:
        return
    export_format = argv[1]
    paths: list[Path] = []
    if export_format == "json" and "--output" in argv:
        paths.append(Path(argv[argv.index("--output") + 1]))
    elif export_format == "all" and "--output-dir" in argv:
        output_dir = Path(argv[argv.index("--output-dir") + 1])
        paths.extend(output_dir.glob("*.json"))

    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload.get("repository"), dict):
            payload["repository"].pop("description", None)
        if "--no-include-readme" in argv:
            payload.pop("readme_content", None)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
