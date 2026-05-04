from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli.extract import main


def test_extract_command_outputs_documents_as_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _make_repo(tmp_path)

    exit_code = main([str(repo)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["document_count"] == 3
    assert [doc["metadata"]["path"] for doc in payload["documents"]] == [
        "README.md",
        "docs/guide.md",
        "notes.txt",
    ]
    assert payload["documents"][0]["metadata"]["title"] == "Project"
    assert payload["documents"][0]["metadata"]["is_readme"] is True
    assert payload["documents"][0]["content"].startswith("# Project")


def test_extract_command_writes_json_to_output_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _make_repo(tmp_path)
    output_dir = tmp_path / "out"

    exit_code = main([str(repo), "--output-dir", str(output_dir), "--format", "json"])

    assert exit_code == 0
    assert "documents.json" in capsys.readouterr().out
    payload = json.loads((output_dir / "documents.json").read_text(encoding="utf-8"))
    assert payload["document_count"] == 3
    assert payload["repo_path"] == str(repo)


def test_extract_command_writes_text_documents(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _make_repo(tmp_path)
    output_dir = tmp_path / "text-output"

    exit_code = main([str(repo), "--output-dir", str(output_dir), "--format", "text"])

    assert exit_code == 0
    assert str(output_dir) in capsys.readouterr().out
    readme_output = output_dir / "README.md.txt"
    assert readme_output.exists()
    assert "Path: README.md" in readme_output.read_text(encoding="utf-8")


def test_readme_command_extracts_readme_with_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _make_repo(tmp_path)

    exit_code = main(["readme", str(repo), "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["document_count"] == 1
    metadata = payload["documents"][0]["metadata"]
    assert metadata["path"] == "README.md"
    assert metadata["title"] == "Project"
    assert metadata["is_readme"] is True


def test_readme_command_writes_readme_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _make_repo(tmp_path)
    output_dir = tmp_path / "readme-out"

    exit_code = main(["readme", str(repo), "--output-dir", str(output_dir)])

    assert exit_code == 0
    assert "readme.json" in capsys.readouterr().out
    payload = json.loads((output_dir / "readme.json").read_text(encoding="utf-8"))
    assert payload["document_count"] == 1


def test_extract_command_reports_invalid_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_repo = tmp_path / "missing"

    exit_code = main([str(missing_repo)])

    assert exit_code == 1
    assert "Repository path does not exist" in capsys.readouterr().err


def test_extract_command_reports_missing_documents(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src.py").write_text("print('not docs')\n", encoding="utf-8")

    exit_code = main([str(repo)])

    assert exit_code == 1
    assert "No supported documents found" in capsys.readouterr().err


def test_readme_command_reports_missing_readme(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "guide.md").write_text("# Guide\n", encoding="utf-8")

    exit_code = main(["readme", str(repo)])

    assert exit_code == 1
    assert "No README document found" in capsys.readouterr().err


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    docs = repo / "docs"
    git_dir = repo / ".git"
    docs.mkdir(parents=True)
    git_dir.mkdir(parents=True)
    (repo / "README.md").write_text("# Project\n\nMain documentation.\n", encoding="utf-8")
    (docs / "guide.md").write_text("# Guide\n\nUsage notes.\n", encoding="utf-8")
    (repo / "notes.txt").write_text("Plain text notes\n", encoding="utf-8")
    (git_dir / "README.md").write_text("# Ignored\n", encoding="utf-8")
    (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
    return repo
