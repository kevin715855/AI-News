"""Workflow integration for validating localized README output before acceptance."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .base import ValidationResult, ValidationRule, Validator
from .config import ValidatorConfig
from .rules import default_rules


@dataclass
class RuleReport:
    """Validation outcome for one rule."""

    rule_name: str
    result: ValidationResult

    @property
    def status(self) -> str:
        return "FAIL" if self.result.errors else "PASS"


@dataclass
class ValidationReport:
    """Formatted validation report for one localized README."""

    path: Path
    rules: list[RuleReport] = field(default_factory=list)

    @property
    def errors(self) -> list[str]:
        return [error for rule in self.rules for error in rule.result.errors]

    @property
    def warnings(self) -> list[str]:
        return [warning for rule in self.rules for warning in rule.result.warnings]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def exit_code(self, strict: bool = False) -> int:
        if self.errors:
            return 1
        if strict and self.warnings:
            return 2
        return 0

    def format(self) -> str:
        lines = [f"Validation report: {self.path}"]
        for rule in self.rules:
            lines.append(f"{rule.status} {rule.rule_name}")
            for error in rule.result.errors:
                lines.append(f"  ERROR {self.path}: {error}")
            for warning in rule.result.warnings:
                lines.append(f"  WARNING {self.path}: {warning}")
        return "\n".join(lines)


class QAValidationFailed(Exception):
    """Raised when localized content fails QA validation."""

    def __init__(self, report: ValidationReport) -> None:
        super().__init__(report.format())
        self.report = report


class QAValidator:
    """Runs QA validation before localized README content is accepted."""

    def __init__(
        self,
        rules: list[ValidationRule] | None = None,
        config: ValidatorConfig | None = None,
        strict: bool = False,
    ) -> None:
        self.config = config or ValidatorConfig()
        self.rules = list(rules or default_rules())
        self.strict = strict

    def validate_content(self, content: str, path: str | Path) -> ValidationReport:
        """Validate localized content without writing it."""

        report = ValidationReport(Path(path))
        for rule in self.rules:
            if not self.config.is_rule_enabled(rule.rule_name):
                continue
            validator = Validator([rule], self.config)
            report.rules.append(RuleReport(rule.rule_name, validator.validate(content)))
        return report

    def validate_file(self, readme_path: str | Path) -> ValidationReport:
        """Validate a localized README file from disk."""

        path = Path(readme_path)
        content = path.read_text(encoding="utf-8")
        return self.validate_content(content, path)

    def assert_valid_content(self, content: str, path: str | Path) -> ValidationReport:
        """Validate content and raise if errors or strict warnings are present."""

        report = self.validate_content(content, path)
        if report.exit_code(strict=self.strict) != 0:
            raise QAValidationFailed(report)
        return report

    def assert_valid_file(self, readme_path: str | Path) -> ValidationReport:
        """Validate a localized README file and raise when it cannot be accepted."""

        report = self.validate_file(readme_path)
        if report.exit_code(strict=self.strict) != 0:
            raise QAValidationFailed(report)
        return report

    def write_localized_readme(self, content: str, destination: str | Path) -> Path:
        """Validate content before writing the final localized README."""

        path = Path(destination)
        self.assert_valid_content(content, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def validate_before_write(self, content: str, destination: str | Path) -> ValidationReport:
        """Pre-commit style hook for localization pipelines."""

        return self.assert_valid_content(content, destination)
