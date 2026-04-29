"""Base validation framework for digest QA checks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .config import ValidationSeverity, ValidatorConfig


@dataclass(frozen=True)
class ValidationError:
    """Structured validation finding emitted by rules or the runner."""

    rule_name: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    line: int | None = None
    column: int | None = None
    code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", ValidationSeverity(self.severity))

    def format(self) -> str:
        """Render the finding as a stable, human-readable message."""

        location_parts = []
        if self.line is not None:
            location_parts.append(f"line {self.line}")
        if self.column is not None:
            location_parts.append(f"column {self.column}")

        prefix = f"[{self.rule_name}]"
        if self.code:
            prefix = f"{prefix} {self.code}:"

        location = f" ({', '.join(location_parts)})" if location_parts else ""
        return f"{prefix} {self.message}{location}"


@dataclass
class ValidationResult:
    """Aggregated result for one or more validation rules."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, error: ValidationError | str) -> None:
        """Record an error and mark the result invalid."""

        self.errors.append(_format_finding(error))
        self.is_valid = False

    def add_warning(self, warning: ValidationError | str) -> None:
        """Record a warning without changing validity."""

        self.warnings.append(_format_finding(warning))

    def extend(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""

        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.is_valid = self.is_valid and other.is_valid and not self.errors

    @classmethod
    def valid(cls) -> "ValidationResult":
        """Create a passing validation result."""

        return cls()

    @classmethod
    def invalid(
        cls,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> "ValidationResult":
        """Create a failing validation result."""

        return cls(
            is_valid=False,
            errors=list(errors or []),
            warnings=list(warnings or []),
        )


class ValidationRule(ABC):
    """Abstract base class for custom content validation rules."""

    name: str | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR

    @property
    def rule_name(self) -> str:
        """Return the configured rule name or the class name."""

        return self.name or self.__class__.__name__

    @abstractmethod
    def validate(
        self,
        content: str,
        source_content: str | None = None,
    ) -> ValidationResult:
        """Validate content and return all findings for this rule."""


class Validator:
    """Runs validation rules and aggregates their results."""

    def __init__(
        self,
        rules: list[ValidationRule] | None = None,
        config: ValidatorConfig | None = None,
    ) -> None:
        self.rules = list(rules or [])
        self.config = config or ValidatorConfig()

    def add_rule(self, rule: ValidationRule) -> None:
        """Append a rule to the validator."""

        self.rules.append(rule)

    def validate(
        self,
        content: str,
        source_content: str | None = None,
    ) -> ValidationResult:
        """Run all enabled rules and collect every failure."""

        result = ValidationResult.valid()
        for rule in self.rules:
            if not self.config.is_rule_enabled(rule.rule_name):
                continue

            try:
                if source_content is None:
                    rule_result = rule.validate(content)
                else:
                    rule_result = rule.validate(content, source_content=source_content)
            except Exception as exc:  # pragma: no cover - exact exception varies
                rule_result = ValidationResult.invalid(
                    [
                        ValidationError(
                            rule_name=rule.rule_name,
                            message=f"Rule raised {exc.__class__.__name__}: {exc}",
                            severity=ValidationSeverity.ERROR,
                            code="RULE_EXCEPTION",
                        ).format()
                    ]
                )

            result.extend(self._apply_configured_severity(rule, rule_result))

        result.is_valid = not result.errors
        return result

    def _apply_configured_severity(
        self, rule: ValidationRule, rule_result: ValidationResult
    ) -> ValidationResult:
        severity = self.config.get_rule_severity(rule.rule_name, rule.severity)
        if severity == ValidationSeverity.WARNING and rule_result.errors:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=rule_result.warnings + rule_result.errors,
            )
        if severity == ValidationSeverity.INFO and rule_result.errors:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=rule_result.warnings,
            )
        return rule_result


def _format_finding(finding: ValidationError | str) -> str:
    if isinstance(finding, ValidationError):
        return finding.format()
    return finding
