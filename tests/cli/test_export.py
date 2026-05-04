import json
from pathlib import Path

import pytest

from cli.export import build_export_data, main


def _sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text(
        "# Sample Repo\n\nTóm tắt tiếng Việt cho repository.",
        encoding="utf-8",
    )
    (repo / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    return repo


def test_build_export_data_from_local_repo(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path)

    data = build_export_data(repo)

    assert data.repo_name == "sample-repo"
    assert data.summary == "Tóm tắt tiếng Việt cho repository."
    assert data.description == "Sample Repo"
    assert data.metadata["language"] == "Python"
    assert "README.md" in data.source_files


def test_export_markdown_command_generates_file(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path)
    output = tmp_path / "summary.md"

    exit_code = main(["export", "markdown", str(repo), "--output", str(output)])

    assert exit_code == 0
    content = output.read_text(encoding="utf-8")
    assert "# sample-repo" in content
    assert "Tóm tắt tiếng Việt" in content
    assert "## README da Viet hoa" in content


def test_export_json_command_generates_parseable_json(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path)
    output = tmp_path / "summary.json"

    exit_code = main(["export", "json", str(repo), "--output", str(output)])

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["repository"]["name"] == "sample-repo"
    assert payload["summary"] == "Tóm tắt tiếng Việt cho repository."
    assert payload["metadata"]["readme"] == "README.md"


def test_export_all_command_generates_both_formats(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path)
    output_dir = tmp_path / "exports"

    exit_code = main(["export", "all", str(repo), "--output-dir", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "sample-repo.md").exists()
    assert (output_dir / "sample-repo.json").exists()


def test_include_readme_flag_controls_output(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path)
    output = tmp_path / "summary.json"

    exit_code = main(
        ["export", "json", str(repo), "--output", str(output), "--no-include-readme"]
    )

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["readme_content"] is None


def test_export_command_rejects_missing_repo(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["export", "json", str(tmp_path / "missing"), "--output", str(tmp_path / "out.json")])

    assert exc.value.code == 2
