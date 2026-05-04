from validator.trending import TrendingFetcher


SAMPLE_TRENDING_HTML = """
<main>
  <article class="Box-row">
    <h2><a href="/octo/hello-world"> octo / hello-world </a></h2>
    <p> Sample project description. </p>
    <span itemprop="programmingLanguage">Python</span>
    <a href="/octo/hello-world/stargazers">1,234</a>
    <a href="/octo/hello-world/forks">56</a>
    <span class="d-inline-block float-sm-right">123 stars today</span>
  </article>
  <article class="Box-row">
    <h2><a href="/acme/repo-two">acme/repo-two</a></h2>
    <p>Second repository.</p>
    <span itemprop="programmingLanguage">Go</span>
    <a href="/acme/repo-two/stargazers">500</a>
    <a href="/acme/repo-two/forks">44</a>
    <span class="d-inline-block float-sm-right">20 stars today</span>
  </article>
</main>
"""


def test_fetcher_parses_repositories_from_trending_html() -> None:
    fetcher = TrendingFetcher()

    repositories = list(fetcher._parse_repositories(SAMPLE_TRENDING_HTML))

    assert len(repositories) == 2
    assert repositories[0].name == "octo/hello-world"
    assert repositories[0].url == "https://github.com/octo/hello-world"
    assert repositories[0].description == "Sample project description."
    assert repositories[0].language == "Python"
    assert repositories[0].stars == 1234
    assert repositories[0].forks == 56
    assert repositories[0].stars_today == 123


def test_fetcher_builds_language_url_and_applies_limit() -> None:
    class StubFetcher(TrendingFetcher):
        def __init__(self) -> None:
            self.captured_urls: list[str] = []

        def _download(self, url: str) -> str:
            self.captured_urls.append(url)
            return SAMPLE_TRENDING_HTML

    fetcher = StubFetcher()

    repositories = fetcher.fetch(language="python", since="weekly", limit=1)

    assert fetcher.captured_urls == ["https://github.com/trending/python?since=weekly"]
    assert len(repositories) == 1
    assert repositories[0].name == "octo/hello-world"
