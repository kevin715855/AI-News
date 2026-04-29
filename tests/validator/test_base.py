import pytest

from src.validator import (
    ValidationError,
    ValidationResult,
    ValidationRule,
    ValidationSeverity,
    Validator,
    ValidatorConfig,
)


class AlwaysPassRule(ValidationRule):
    def validate(self, content: str) -> ValidationResult:
        return ValidationResult.valid()


class MultiFailureRule(ValidationRule):
    name = "multi_failure"

    def validate(self, content: str) -> ValidationResult:
        result = ValidationResult.valid()
        result.add_error("missing heading")
        result.add_error("missing source link")
        result.add_warning("translation could be more natural")
        return result


class WarningRule(ValidationRule):
    name = "warning_rule"

    def validate(self, content: str) -> ValidationResult:
        result = ValidationResult.valid()
        result.add_warning("minor style issue")
        return result


class ExplodingRule(ValidationRule):
    name = "exploding"

    def validate(self, content: str) -> ValidationResult:
        raise RuntimeError("unexpected parser failure")


def test_validation_rule_is_abstract() -> None:
    with pytest.raises(TypeError):
        ValidationRule()


def test_validator_runs_multiple_rules_and_aggregates_results() -> None:
    validator = Validator([AlwaysPassRule(), MultiFailureRule(), WarningRule()])

    result = validator.validate("# Digest")

    assert result.is_valid is False
    assert result.errors == ["missing heading", "missing source link"]
    assert result.warnings == [
        "translation could be more natural",
        "minor style issue",
    ]


def test_validator_does_not_stop_after_first_failure() -> None:
    validator = Validator([MultiFailureRule(), ExplodingRule(), MultiFailureRule()])

    result = validator.validate("")

    assert len(result.errors) == 5
    assert "Rule raised RuntimeError" in result.errors[2]
    assert result.errors[3:] == ["missing heading", "missing source link"]


def test_config_can_disable_specific_rules() -> None:
    config = ValidatorConfig(disabled_rules={"multi_failure"})
    validator = Validator([MultiFailureRule(), WarningRule()], config=config)

    result = validator.validate("")

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == ["minor style issue"]


def test_config_enabled_rules_allowlist() -> None:
    config = ValidatorConfig(enabled_rules={"warning_rule"})
    validator = Validator([MultiFailureRule(), WarningRule()], config=config)

    result = validator.validate("")

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == ["minor style issue"]


def test_config_enable_disable_helpers_update_rule_sets() -> None:
    config = ValidatorConfig()

    config.disable_rule("markdown")
    assert config.is_rule_enabled("markdown") is False

    config.enable_rule("markdown")
    assert config.is_rule_enabled("markdown") is True
    assert "markdown" in config.enabled_rules
    assert "markdown" not in config.disabled_rules


def test_config_severity_override_can_downgrade_errors_to_warnings() -> None:
    config = ValidatorConfig()
    config.set_rule_severity("multi_failure", ValidationSeverity.WARNING)
    validator = Validator([MultiFailureRule()], config=config)

    result = validator.validate("")

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == [
        "translation could be more natural",
        "missing heading",
        "missing source link",
    ]


def test_info_severity_override_suppresses_error_failures() -> None:
    config = ValidatorConfig()
    config.set_rule_severity("multi_failure", "info")
    validator = Validator([MultiFailureRule()], config=config)

    result = validator.validate("")

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == ["translation could be more natural"]


def test_validation_error_formats_structured_context() -> None:
    error = ValidationError(
        rule_name="link_validity",
        message="URL is unreachable",
        severity=ValidationSeverity.ERROR,
        line=12,
        column=5,
        code="BROKEN_LINK",
    )

    result = ValidationResult.valid()
    result.add_error(error)

    assert result.is_valid is False
    assert result.errors == [
        "[link_validity] BROKEN_LINK: URL is unreachable (line 12, column 5)"
    ]


def test_validation_result_extend_preserves_warnings_and_invalidity() -> None:
    base = ValidationResult.valid()
    base.add_warning("first warning")

    base.extend(ValidationResult.invalid(errors=["hard failure"], warnings=["second warning"]))

    assert base.is_valid is False
    assert base.errors == ["hard failure"]
    assert base.warnings == ["first warning", "second warning"]
