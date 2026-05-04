from pathlib import Path

import pytest

from cli.main import main as main_cli
from cli.trending import fetch_command, list_command
from trending_fetcher import (
    GitHubTrendingFetcher,
    TrendingFetchError,
    TrendingRepository,
    parse_trending_html,
)


TRENDING_HTML = """
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/owner-one/project-one"> owner-one / project-one </a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">First description.</p>
  <span itemprop="programmingLanguage">Python</span>
  <a href="/owner-one/project-one/stargazers">1,234</a>
  <a href="/owner-one/project-one/forks">56</a>
  <span class="d-inline-block float-sm-right">99 stars today</span>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/owner-two/project-two"> owner-two / project-two </a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">Second description.</p>
  <span itemprop="programmingLanguage">Rust</span>
  <a href="/owner-two/project-two/stargazers">2,000</a>
  <a href="/owner-two/project-two/forks">100</a>
  <span class="d-inline-block float-sm-right">12 stars this week</span>
</article>
"""


class RecordingFetcher(GitHubTrendingFetcher):
    def __init__(self, repositories: list[TrendingRepository]) -> None:
        self.repositories = repositories
        self.calls: list[dict[str, object]] = []

    def fetch(
        self,
        language: str | None = None,
        period: str = "daily",
        limit: int = 25,
    ) -> list[TrendingRepository]:
        self.calls.append({"language": language, "period": period, "limit": limit})
        if limit < 1:
            raise ValueError("Limit must be at least 1.")
        return self.repositories[:limit]


class FailingFetcher(GitHubTrendingFetcher):
    def fetch(
        self,
        language: str | None = None,
        period: str = "daily",
        limit: int = 25,
    ) -> list[TrendingRepository]:
        raise TrendingFetchError("GitHub returned 503")


def test_parse_trending_html_extracts_repository_metadata() -> None:
    repositories = parse_trending_html(TRENDING_HTML)

    assert repositories == [
        TrendingRepository(
            owner="owner-one",
            name="project-one",
            url="https://github.com/owner-one/project-one",
            description="First description.",
            language="Python",
            stars=1234,
            forks=56,
            stars_in_period=99,
        ),
        TrendingRepository(
            owner="owner-two",
            name="project-two",
            url="https://github.com/owner-two/project-two",
            description="Second description.",
            language="Rust",
            stars=2000,
            forks=100,
            stars_in_period=12,
        ),
    ]


def test_parse_trending_html_handles_nested_repository_name_spans() -> None:
    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/TauricResearch/TradingAgents">
          <span>TauricResearch</span>
          /
          <span>TradingAgents</span>
        </a>
      </h2>
    </article>
    """

    repositories = parse_trending_html(html)

    assert repositories == [
        TrendingRepository(
            owner="TauricResearch",
            name="TradingAgents",
            url="https://github.com/TauricResearch/TradingAgents",
        )
    ]


def test_fetch_command_passes_options_writes_cache_and_prints_table(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cache_path = tmp_path / "trending.json"
    fetcher = RecordingFetcher(
        [
            TrendingRepository(
                owner="owner-one",
                name="project-one",
                url="https://github.com/owner-one/project-one",
                language="Python",
                stars=1234,
                stars_in_period=99,
            ),
            TrendingRepository(
                owner="owner-two",
                name="project-two",
                url="https://github.com/owner-two/project-two",
                language="Rust",
                stars=2000,
                stars_in_period=12,
            ),
        ]
    )

    exit_code = fetch_command(
        language="python",
        period="weekly",
        limit=1,
        cache_path=cache_path,
        fetcher=fetcher,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert fetcher.calls == [{"language": "python", "period": "weekly", "limit": 1}]
    assert "Fetched 1 repositories." in output
    assert "owner-one/project-one" in output
    assert "owner-two/project-two" not in output
    assert "owner-one" in cache_path.read_text(encoding="utf-8")


def test_fetch_command_treats_empty_language_as_all_languages(
    tmp_path: Path,
) -> None:
    fetcher = RecordingFetcher([])

    exit_code = fetch_command(
        language="",
        period="daily",
        limit=25,
        cache_path=tmp_path / "trending.json",
        fetcher=fetcher,
    )

    assert exit_code == 0
    assert fetcher.calls == [{"language": None, "period": "daily", "limit": 25}]


def test_fetch_command_reports_invalid_limit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = fetch_command(
        language="python",
        period="daily",
        limit=0,
        cache_path=tmp_path / "trending.json",
        fetcher=RecordingFetcher([]),
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Limit must be at least 1" in captured.err


def test_fetch_command_reports_fetch_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = fetch_command(
        language="python",
        period="daily",
        limit=10,
        cache_path=tmp_path / "trending.json",
        fetcher=FailingFetcher(),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "GitHub returned 503" in captured.err


def test_list_command_displays_cached_repositories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cache_path = tmp_path / "trending.json"
    fetch_command(
        language="python",
        period="daily",
        limit=1,
        cache_path=cache_path,
        fetcher=RecordingFetcher(
            [
                TrendingRepository(
                    owner="owner-one",
                    name="project-one",
                    url="https://github.com/owner-one/project-one",
                    description="A useful project.",
                    language="Python",
                    stars=1234,
                    stars_in_period=99,
                )
            ]
        ),
    )
    capsys.readouterr()

    exit_code = list_command(cache_path=cache_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Repository" in output
    assert "owner-one/project-one" in output
    assert "A useful project." in output


def test_list_command_reports_missing_cache(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = list_command(cache_path=tmp_path / "missing.json")

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Run `trending fetch` first" in output


def test_main_cli_routes_trending_list_with_env_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cache_path = tmp_path / "trending.json"
    fetch_command(
        language="",
        period="daily",
        limit=1,
        cache_path=cache_path,
        fetcher=RecordingFetcher(
            [
                TrendingRepository(
                    owner="owner-one",
                    name="project-one",
                    url="https://github.com/owner-one/project-one",
                )
            ]
        ),
    )
    capsys.readouterr()
    monkeypatch.setenv("GITHUB_TRENDING_CACHE", str(cache_path))

    exit_code = main_cli(["trending", "list"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "owner-one/project-one" in output
