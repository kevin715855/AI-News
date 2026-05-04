"""GitHub Trending fetcher and parser."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from typing import Iterable
from urllib.parse import quote
from urllib.request import Request, urlopen
import re

_TRENDING_URL = "https://github.com/trending"
_VALID_SINCE = {"daily", "weekly", "monthly"}


@dataclass(frozen=True)
class RepositoryTrend:
    """One repository entry from the GitHub Trending page."""

    name: str
    url: str
    description: str
    language: str
    stars: int
    forks: int
    stars_today: int

    def to_dict(self) -> dict[str, str | int]:
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "language": self.language,
            "stars": self.stars,
            "forks": self.forks,
            "stars_today": self.stars_today,
        }


class TrendingFetcher:
    """Fetch and parse repositories from GitHub Trending."""

    def fetch(
        self,
        language: str | None = None,
        since: str = "daily",
        limit: int = 10,
    ) -> list[RepositoryTrend]:
        if since not in _VALID_SINCE:
            raise ValueError("since must be one of: daily, weekly, monthly")
        if limit <= 0:
            raise ValueError("limit must be greater than 0")

        html = self._download(self._build_url(language=language, since=since))
        repositories = list(self._parse_repositories(html))
        return repositories[:limit]

    def _build_url(self, language: str | None, since: str) -> str:
        base = _TRENDING_URL
        if language:
            base = f"{base}/{quote(language.strip())}"
        return f"{base}?since={since}"

    def _download(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "github-trending-vi-digest/0.1 (+https://github.com)"
            },
        )
        with urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")

    def _parse_repositories(self, html: str) -> Iterable[RepositoryTrend]:
        for article in _extract_articles(html):
            repo = _parse_repository(article)
            if repo is not None:
                yield repo


def _extract_articles(html: str) -> list[str]:
    return re.findall(
        r"<article[^>]*class=\"[^\"]*Box-row[^\"]*\"[^>]*>(.*?)</article>",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def _parse_repository(article_html: str) -> RepositoryTrend | None:
    name_match = re.search(
        r"<h2[^>]*>.*?<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>",
        article_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not name_match:
        return None

    href = name_match.group(1).strip()
    raw_name = _clean_text(name_match.group(2))
    if not raw_name:
        return None

    description_match = re.search(
        r"<p[^>]*>(.*?)</p>",
        article_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    language_match = re.search(
        r"itemprop=\"programmingLanguage\"[^>]*>(.*?)</span>",
        article_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stars_match = re.search(
        r"<a[^>]*href=\"[^\"]*/stargazers\"[^>]*>(.*?)</a>",
        article_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    forks_match = re.search(
        r"<a[^>]*href=\"[^\"]*/forks\"[^>]*>(.*?)</a>",
        article_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    today_match = re.search(
        r"(\d[\d,]*)\s+stars\s+today",
        article_html,
        flags=re.IGNORECASE,
    )

    return RepositoryTrend(
        name=re.sub(r"\s*/\s*", "/", raw_name),
        url=_absolute_repo_url(href),
        description=_clean_text(description_match.group(1)) if description_match else "",
        language=_clean_text(language_match.group(1)) if language_match else "",
        stars=_extract_number(stars_match.group(1)) if stars_match else 0,
        forks=_extract_number(forks_match.group(1)) if forks_match else 0,
        stars_today=_extract_number(today_match.group(1)) if today_match else 0,
    )


def _absolute_repo_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"https://github.com/{href.lstrip('/')}"


def _extract_number(raw: str) -> int:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else 0


def _clean_text(raw: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", raw)
    normalized = re.sub(r"\s+", " ", unescape(without_tags)).strip()
    return normalized
