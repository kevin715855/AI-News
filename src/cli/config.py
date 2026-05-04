"""Configuration loading for the github-trending-vi-digest CLI."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CLIConfig:
    """Runtime configuration shared by CLI commands."""

    verbose: bool = False
    config_path: Path | None = None
    output_dir: Path = Path("dist")

    @classmethod
    def load(
        cls,
        config_path: Path | None = None,
        output_dir: Path | None = None,
        verbose: bool = False,
    ) -> "CLIConfig":
        values: dict[str, Any] = {}
        if config_path is not None:
            values = _load_json_config(config_path)

        configured_output = values.get("output_dir")
        resolved_output = output_dir
        if resolved_output is None and configured_output:
            resolved_output = Path(str(configured_output))

        return cls(
            verbose=verbose,
            config_path=config_path,
            output_dir=resolved_output or Path("dist"),
        )


def _load_json_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)

    if not isinstance(data, dict):
        raise ValueError("Config file must contain a JSON object.")

    return data
