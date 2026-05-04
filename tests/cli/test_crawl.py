from pathlib import Path

import pytest

from cli.crawl import main
from crawler import CrawlError, LocalRepoCrawler


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")

    package = repo / "package"
    package.mkdir()
    (package / "index.ts").write_text("export const value = 1;\n", encoding="utf-8")

    nested = package / "nested"
    nested.mkdir()
    (nested / "deep.py").write_text("value = 1\n", encoding="utf-8")
    return repo


def test_crawl_analyzes_local_repository_and_writes_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = make_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main([str(repo)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Crawl status:" in output
    assert "Files analyzed: 3" in output
    assert "Documentation files: 0" in output
    assert "Python: 2" in output
    assert (tmp_path / ".crawl-status.json").exists()


def test_crawl_include_docs_counts_documentation_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = make_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main([str(repo), "--include-docs"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Files analyzed: 4" in output
    assert "Documentation files: 1" in output
    assert "Markdown: 1" in output


def test_crawl_depth_limits_nested_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = make_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main([str(repo), "--depth", "1"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Files analyzed: 2" in output
    assert "Directories scanned: 2" in output
    assert "Python: 1" in output


def test_crawl_status_displays_latest_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = make_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert main([str(repo), "--include-docs"]) == 0
    capsys.readouterr()

    assert main(["status"]) == 0

    output = capsys.readouterr().out
    assert "Files analyzed: 4" in output
    assert str(repo.resolve()) in output


def test_crawl_status_reports_missing_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["status"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "No crawl status found." in output


def test_crawl_rejects_missing_path(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["missing-repo"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Repository path does not exist" in output


def test_crawl_rejects_directory_without_git_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "not-a-repo"
    repo.mkdir()

    exit_code = main([str(repo)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Missing git repository metadata" in output


def test_crawler_rejects_negative_depth() -> None:
    with pytest.raises(CrawlError, match="--depth must be zero or greater"):
        LocalRepoCrawler(depth=-1)
