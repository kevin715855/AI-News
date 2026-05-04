from pathlib import Path

import pytest

from src.cli.config import CLIConfig
from src.cli.main import COMMANDS, build_parser, main


def test_help_text_lists_global_options_and_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["--help"])

    output = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "--verbose" in output
    assert "--config" in output
    assert "--output-dir" in output
    for command_name, _ in COMMANDS:
        assert command_name in output


def test_command_group_runs_with_global_options_before_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_dir = tmp_path / "digest"

    exit_code = main(["--verbose", "--output-dir", str(output_dir), "trending"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Config: output_dir=" in output
    assert str(output_dir) in output
    assert "trending: command group is ready." in output


def test_command_group_runs_with_global_options_after_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_dir = tmp_path / "localized"

    exit_code = main(["localize", "--verbose", "--output-dir", str(output_dir)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert str(output_dir) in output
    assert "localize: command group is ready." in output


@pytest.mark.parametrize("command_name", [name for name, _ in COMMANDS])
def test_all_command_groups_are_registered(
    command_name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main([command_name])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"{command_name}: command group is ready." in output


def test_version_option_displays_package_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["--version"])

    output = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "github-trending-vi-digest 0.1.0" in output


def test_config_loads_output_dir_from_json(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"output_dir": "out/from-config"}', encoding="utf-8")

    config = CLIConfig.load(config_path=config_path)

    assert config.config_path == config_path
    assert config.output_dir == Path("out/from-config")


def test_cli_output_dir_overrides_config_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"output_dir": "out/from-config"}', encoding="utf-8")
    output_dir = tmp_path / "override"

    exit_code = main(
        [
            "--verbose",
            "--config",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "export",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert str(output_dir) in output
    assert "out/from-config" not in output


def test_missing_config_file_returns_parser_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--config", str(tmp_path / "missing.json"), "validate"])

    error = capsys.readouterr().err
    assert exc_info.value.code == 2
    assert "Config file does not exist" in error


def test_non_object_config_file_returns_parser_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('["not", "an", "object"]', encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(["--config", str(config_path), "crawl"])

    error = capsys.readouterr().err
    assert exc_info.value.code == 2
    assert "Config file must contain a JSON object" in error
