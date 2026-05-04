import json
from pathlib import Path

import pytest

from validator import cli
from validator.trending import RepositoryTrend


def test_fetch_command_writes_json_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_file = tmp_path / "trending.json"

    class FakeFetcher:
        def fetch(self, language: str | None, since: str, limit: int) -> list[RepositoryTrend]:
            assert language == "python"
            assert since == "daily"
            assert limit == 1
            return [
                RepositoryTrend(
                    name="octo/hello-world",
                    url="https://github.com/octo/hello-world",
                    description="Demo",
                    language="Python",
                    stars=100,
                    forks=10,
                    stars_today=5,
                )
            ]

    original_fetcher = cli.TrendingFetcher
    cli.TrendingFetcher = FakeFetcher
    try:
        exit_code = cli.main(
            [
                "fetch",
                "--language",
                "python",
                "--since",
                "daily",
                "--limit",
                "1",
                "--output-file",
                str(output_file),
            ]
        )
    finally:
        cli.TrendingFetcher = original_fetcher

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Wrote 1 repositories" in output
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload[0]["name"] == "octo/hello-world"


def test_fetch_command_prints_error_on_network_failure(capsys: pytest.CaptureFixture[str]) -> None:
    class FailingFetcher:
        def fetch(self, language: str | None, since: str, limit: int) -> list[RepositoryTrend]:
            raise TimeoutError("timed out")

    original_fetcher = cli.TrendingFetcher
    cli.TrendingFetcher = FailingFetcher
    try:
        exit_code = cli.main(["fetch"])
    finally:
        cli.TrendingFetcher = original_fetcher

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Fetch failed" in output
