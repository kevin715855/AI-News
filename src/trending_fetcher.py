"""Fetch and parse GitHub Trending repositories."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


VALID_PERIODS = {"daily", "weekly", "monthly"}


class TrendingFetchError(RuntimeError):
    """Raised when GitHub Trending cannot be fetched or parsed."""


@dataclass(frozen=True)
class TrendingRepository:
    owner: str
    name: str
    url: str
    description: str = ""
    language: str = ""
    stars: int = 0
    forks: int = 0
    stars_in_period: int = 0

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"full_name": self.full_name}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TrendingRepository":
        return cls(
            owner=str(data["owner"]),
            name=str(data["name"]),
            url=str(data["url"]),
            description=str(data.get("description", "")),
            language=str(data.get("language", "")),
            stars=int(data.get("stars", 0)),
            forks=int(data.get("forks", 0)),
            stars_in_period=int(data.get("stars_in_period", 0)),
        )


class GitHubTrendingFetcher:
    base_url = "https://github.com/trending"

    def fetch(
        self,
        language: str | None = None,
        period: str = "daily",
        limit: int = 25,
    ) -> list[TrendingRepository]:
        self._validate(period=period, limit=limit)
        url = self._build_url(language=language, period=period)
        request = Request(url, headers={"User-Agent": "github-trending-vi-digest/0.1"})

        try:
            with urlopen(request, timeout=20) as response:
                html = response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise TrendingFetchError(f"Unable to fetch GitHub Trending: {exc}") from exc

        repositories = parse_trending_html(html)
        return repositories[:limit]

    def _build_url(self, language: str | None, period: str) -> str:
        language_path = quote(language.strip(), safe="") if language else ""
        suffix = f"/{language_path}" if language_path else ""
        return f"{self.base_url}{suffix}?since={period}"

    def _validate(self, period: str, limit: int) -> None:
        if period not in VALID_PERIODS:
            allowed = ", ".join(sorted(VALID_PERIODS))
            raise ValueError(f"Invalid period '{period}'. Expected one of: {allowed}.")
        if limit < 1:
            raise ValueError("Limit must be at least 1.")


def parse_trending_html(html: str) -> list[TrendingRepository]:
    parser = _TrendingHTMLParser()
    parser.feed(html)
    return parser.repositories


class _TrendingHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.repositories: list[TrendingRepository] = []
        self._current: dict[str, object] | None = None
        self._article_depth = 0
        self._capture: str | None = None
        self._capture_tag: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        class_name = attr_map.get("class", "")

        if tag == "article" and "Box-row" in class_name:
            self._current = {}
            self._article_depth = 1
            return

        if self._current is None:
            return

        self._article_depth += 1

        if tag == "a" and self._is_repository_href(attr_map.get("href", "")):
            self._start_capture("repository", tag)
            self._current["href"] = attr_map["href"]
        elif tag == "p" and "col-9" in class_name:
            self._start_capture("description", tag)
        elif tag == "span" and attr_map.get("itemprop") == "programmingLanguage":
            self._start_capture("language", tag)
        elif tag == "a" and attr_map.get("href", "").endswith("/stargazers"):
            self._start_capture("stars", tag)
        elif tag == "a" and attr_map.get("href", "").endswith("/forks"):
            self._start_capture("forks", tag)
        elif tag == "span" and "float-sm-right" in class_name:
            self._start_capture("stars_in_period", tag)

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return

        if self._capture and tag == self._capture_tag:
            self._finish_capture()

        if tag == "article":
            self._finish_repository()
            self._current = None
            self._article_depth = 0
            return

        self._article_depth = max(0, self._article_depth - 1)

    def _start_capture(self, field: str, tag: str) -> None:
        if self._capture is None:
            self._capture = field
            self._capture_tag = tag
            self._text = []

    def _finish_capture(self) -> None:
        if self._current is None or self._capture is None:
            return
        value = _normalize_text(" ".join(self._text))
        if value and self._capture not in self._current:
            self._current[self._capture] = value
        self._capture = None
        self._capture_tag = None
        self._text = []

    def _finish_repository(self) -> None:
        if not self._current or "repository" not in self._current:
            return
        owner, name = _parse_full_name(str(self._current["repository"]))
        self.repositories.append(
            TrendingRepository(
                owner=owner,
                name=name,
                url=f"https://github.com/{owner}/{name}",
                description=str(self._current.get("description", "")),
                language=str(self._current.get("language", "")),
                stars=_parse_count(self._current.get("stars")),
                forks=_parse_count(self._current.get("forks")),
                stars_in_period=_parse_count(self._current.get("stars_in_period")),
            )
        )

    def _is_repository_href(self, href: str) -> bool:
        parts = [part for part in href.split("/") if part]
        return len(parts) == 2 and not href.endswith(("/stargazers", "/forks"))


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())


def _parse_full_name(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.replace("\n", "").split("/") if part.strip()]
    if len(parts) != 2:
        raise TrendingFetchError(f"Unable to parse repository name: {value!r}")
    return parts[0], parts[1]


def _parse_count(value: object) -> int:
    if value is None:
        return 0
    digits = "".join(character for character in str(value) if character.isdigit())
    return int(digits) if digits else 0


def repositories_to_dicts(
    repositories: Iterable[TrendingRepository],
) -> list[dict[str, object]]:
    return [repository.to_dict() for repository in repositories]
