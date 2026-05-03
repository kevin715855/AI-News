from pathlib import Path
import time

import pytest

from validator.cli import main, validate_localized_main
from validator.workflow import QAValidationFailed, QAValidator


VALID_README = """# Du an

Day la README tieng Viet cho goi `github-trending-vi-digest`.

## Cai dat

```bash
pip install github-trending-vi-digest
```

Xem [tai lieu](https://example.com/docs).
"""


def test_cli_reports_pass_per_rule(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text(VALID_README, encoding="utf-8")

    exit_code = main(["validate-localized", str(readme)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PASS markdown-structure" in output
    assert "PASS heading-hierarchy" in output
    assert "PASS link-integrity" in output
    assert str(readme) in output


def test_console_script_entry_validates_without_subcommand(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text(VALID_README, encoding="utf-8")

    exit_code = validate_localized_main([str(readme)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PASS markdown-structure" in output
    assert str(readme) in output


def test_cli_returns_one_for_validation_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text("# Du an\n\n```bash\npip install demo\n", encoding="utf-8")

    exit_code = main(["validate-localized", str(readme)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL markdown-structure" in output
    assert str(readme) in output
    assert "line 3" in output
    assert "markdown-structure" in output
    assert "Unclosed fenced code block" in output


def test_cli_strict_returns_two_for_warnings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text("# Project\n\nEnglish only prose.\n", encoding="utf-8")

    exit_code = main(["validate-localized", str(readme), "--strict"])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "WARNING" in output
    assert "vietnamese-localization" in output


def test_cli_runs_selected_rules_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text("# Project\n\nEnglish only prose.\n", encoding="utf-8")

    exit_code = main(
        [
            "validate-localized",
            str(readme),
            "--strict",
            "--rules",
            "markdown-structure",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PASS markdown-structure" in output
    assert "vietnamese-localization" not in output


def test_qa_validator_prevents_failed_localized_output(tmp_path: Path) -> None:
    destination = tmp_path / "localized" / "README.vi.md"
    validator = QAValidator()

    with pytest.raises(QAValidationFailed) as exc_info:
        validator.write_localized_readme("# Du an\n\n```bash\npip install demo\n", destination)

    assert not destination.exists()
    assert str(destination) in str(exc_info.value)
    assert "markdown-structure" in str(exc_info.value)


def test_qa_validator_writes_valid_localized_output(tmp_path: Path) -> None:
    destination = tmp_path / "localized" / "README.vi.md"
    validator = QAValidator()

    written = validator.write_localized_readme(VALID_README, destination)

    assert written == destination
    assert destination.read_text(encoding="utf-8") == VALID_README


def test_typical_readme_validates_under_one_second(tmp_path: Path) -> None:
    readme = tmp_path / "README.vi.md"
    body = "\n".join(f"Day la dong noi dung tieng Viet so {i}." for i in range(450))
    readme.write_text(f"# Du an\n\n{body}\n", encoding="utf-8")

    start = time.perf_counter()
    report = QAValidator().validate_file(readme)
    elapsed = time.perf_counter() - start

    assert report.is_valid
    assert elapsed < 1
