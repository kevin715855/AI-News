from pathlib import Path

import pytest

from github_trending_vi_digest import (
    AppConfig,
    DigestItem,
    RepositoryCandidate,
    __version__,
)
from github_trending_vi_digest.cli import main


def test_package_exports_version_and_core_dataclasses() -> None:
    repository = RepositoryCandidate(
        owner="openai",
        name="example",
        url="https://github.com/openai/example",
        topics=("ai",),
    )
    item = DigestItem(repository=repository, summary_vi="Tom tat ngan.")

    assert __version__ == "0.1.0"
    assert repository.full_name == "openai/example"
    assert item.repository is repository
    assert item.highlights_vi == ()


def test_app_config_creates_artifact_layout(tmp_path: Path) -> None:
    config = AppConfig(artifact_dir=tmp_path / "artifacts")

    config.ensure_artifact_dirs()

    assert config.artifact_dir.is_dir()
    for subdir in config.artifact_subdirs:
        assert (config.artifact_dir / subdir).is_dir()


def test_cli_help_lists_init_and_workflow_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    output = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "init" in output
    assert "fetch" in output
    assert "export" in output


def test_cli_init_creates_artifact_directories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact_dir = tmp_path / "digest-artifacts"

    exit_code = main(["--artifact-dir", str(artifact_dir), "init"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert str(artifact_dir) in output
    assert (artifact_dir / "raw").is_dir()
    assert (artifact_dir / "exports").is_dir()


def test_placeholder_commands_return_two(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["fetch"])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "not implemented yet" in output
