"""Configuration for validation rule execution and reporting."""

from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity levels used when reporting validation findings."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidatorConfig:
    """Controls which validation rules run and how findings are classified."""

    enabled_rules: set[str] = field(default_factory=set)
    disabled_rules: set[str] = field(default_factory=set)
    severity_overrides: dict[str, ValidationSeverity] = field(default_factory=dict)

    def is_rule_enabled(self, rule_name: str) -> bool:
        """Return whether a rule should run."""

        if rule_name in self.disabled_rules:
            return False
        return not self.enabled_rules or rule_name in self.enabled_rules

    def enable_rule(self, rule_name: str) -> None:
        """Enable a rule and remove any explicit disabled marker."""

        self.enabled_rules.add(rule_name)
        self.disabled_rules.discard(rule_name)

    def disable_rule(self, rule_name: str) -> None:
        """Disable a rule and remove any explicit enabled marker."""

        self.disabled_rules.add(rule_name)
        self.enabled_rules.discard(rule_name)

    def set_rule_severity(
        self, rule_name: str, severity: ValidationSeverity | str
    ) -> None:
        """Override the severity used when a rule reports failures."""

        self.severity_overrides[rule_name] = ValidationSeverity(severity)

    def get_rule_severity(
        self,
        rule_name: str,
        default: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> ValidationSeverity:
        """Return a configured severity override or the supplied default."""

        return self.severity_overrides.get(rule_name, default)
