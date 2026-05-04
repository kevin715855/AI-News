from pathlib import Path

import pytest

from src.cli.summarize import main


class FailingGenerator:
    def summarize(self, repo_path: Path, language: str = "vi") -> str:
        raise RuntimeError("api unavailable")


def create_repo(tmp_path: Path, name: str = "demo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    (repo / "README.md").write_text(
        "# Demo Project\n\nA small tool for testing summaries.\n",
        encoding="utf-8",
    )
    (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
    return repo


def test_summarize_generates_vietnamese_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = create_repo(tmp_path)

    exit_code = main([str(repo)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Tom tat kho luu tru" in captured.out
    assert "Demo Project" in captured.out
    assert "Python" in captured.out


def test_summarize_writes_output_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = create_repo(tmp_path)
    output = tmp_path / "summary.md"

    exit_code = main([str(repo), "--output", str(output)])

    assert exit_code == 0
    assert "Tom tat kho luu tru" in output.read_text(encoding="utf-8")
    assert capsys.readouterr().out == ""


def test_summarize_language_option_generates_english(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = create_repo(tmp_path)

    exit_code = main([str(repo), "--language", "en"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Repository summary" in captured.out
    assert "Repository name" in captured.out


def test_summarize_batch_prints_multiple_repositories(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    first = create_repo(tmp_path, "first")
    second = create_repo(tmp_path, "second")

    exit_code = main(["batch", str(first), str(second)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "== " in captured.out
    assert "first" in captured.out
    assert "second" in captured.out


def test_summarize_batch_writes_output_directory(tmp_path: Path) -> None:
    first = create_repo(tmp_path, "first")
    second = create_repo(tmp_path, "second")
    output = tmp_path / "summaries"

    exit_code = main(["batch", str(first), str(second), "--output", str(output)])

    assert exit_code == 0
    assert (output / "first.md").exists()
    assert (output / "second.md").exists()


def test_summarize_reports_missing_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing"

    exit_code = main([str(missing)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR" in captured.out
    assert "does not exist" in captured.out


def test_summarize_reports_generator_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = create_repo(tmp_path)

    exit_code = main([str(repo)], generator=FailingGenerator())

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "api unavailable" in captured.out


def test_summarize_batch_continues_after_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = create_repo(tmp_path)
    missing = tmp_path / "missing"

    exit_code = main(["batch", str(missing), str(repo)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR" in captured.out
    assert "Tom tat kho luu tru" in captured.out
