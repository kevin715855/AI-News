from pathlib import Path

from cli.validate import main


VALID_README = """# Du an

Day la README tieng Viet cho goi `github-trending-vi-digest`.

## Cai dat

```bash
pip install github-trending-vi-digest
```

Xem [tai lieu](https://example.com/docs).
"""


def test_validate_file_reports_pass_per_rule(
    tmp_path: Path, capsys
) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text(VALID_README, encoding="utf-8")

    exit_code = main(["validate", str(readme)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PASS markdown-structure" in output
    assert "PASS heading-hierarchy" in output
    assert "PASS link-integrity" in output
    assert str(readme) in output


def test_validate_file_returns_one_for_validation_errors(
    tmp_path: Path, capsys
) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text("# Du an\n\n```bash\npip install demo\n", encoding="utf-8")

    exit_code = main(["validate", str(readme)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL markdown-structure" in output
    assert "line 3" in output
    assert "Unclosed fenced code block" in output


def test_validate_strict_returns_two_for_warnings(
    tmp_path: Path, capsys
) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text("# Project\n\nEnglish only prose.\n", encoding="utf-8")

    exit_code = main(["validate", str(readme), "--strict"])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "WARNING" in output
    assert "vietnamese-localization" in output


def test_validate_runs_selected_rules_only(tmp_path: Path, capsys) -> None:
    readme = tmp_path / "README.vi.md"
    readme.write_text("# Project\n\nEnglish only prose.\n", encoding="utf-8")

    exit_code = main(
        [
            "validate",
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


def test_validate_missing_file_returns_one(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing.md"

    exit_code = main(["validate", str(missing)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL file-exists" in output
    assert "File does not exist" in output


def test_validate_readme_uses_readme_with_all_rules(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n\nEnglish only prose.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["validate", "readme", "--rules", "markdown-structure", "--strict"])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Validation report: README.md" in output
    assert "PASS markdown-structure" in output
    assert "WARNING" in output
    assert "vietnamese-localization" in output
