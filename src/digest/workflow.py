"""Workflow orchestration for Vietnamese digests of GitHub Trending repositories."""

from __future__ import annotations

import html.parser
import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from validator.workflow import QAValidator


ProgressReporter = Callable[[str], None]


@dataclass(frozen=True)
class TrendingRepo:
    """Repository discovered from GitHub Trending."""

    owner: str
    name: str
    url: str
    language: str | None = None

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def safe_name(self) -> str:
        return f"{self.owner}__{self.name}"


@dataclass
class RepoAnalysis:
    """Markdown source files discovered in a cloned repository."""

    repo: TrendingRepo
    readme_path: str | None
    document_paths: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    summary_points: list[str] = field(default_factory=list)


@dataclass
class RepoDigest:
    """Generated workflow artifacts for one repository."""

    repo: TrendingRepo
    summary_path: str | None = None
    localized_readme_path: str | None = None
    validation_report: str | None = None
    validation_exit_code: int | None = None


@dataclass(frozen=True)
class WorkflowOptions:
    """Runtime options for the digest workflow."""

    language: str = "python"
    period: str = "daily"
    limit: int = 5
    output_dir: Path = Path("dist/digest")
    mode: str = "both"
    strict_validation: bool = False


class WorkflowError(RuntimeError):
    """Raised when a workflow step cannot recover."""


class GitHubTrendingClient:
    """Fetch repository links from GitHub Trending without third-party dependencies."""

    base_url = "https://github.com/trending"

    def fetch(self, language: str, period: str, limit: int) -> list[TrendingRepo]:
        params = urllib.parse.urlencode({"since": period})
        url = f"{self.base_url}/{urllib.parse.quote(language)}?{params}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "github-trending-vi-digest/0.1"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
        return _TrendingParser(language=language, limit=limit).parse(body)


class DigestWorkflow:
    """Runs each digest step and persists intermediate state for recovery."""

    def __init__(
        self,
        options: WorkflowOptions,
        trending_client: GitHubTrendingClient | None = None,
        progress: ProgressReporter | None = None,
    ) -> None:
        self.options = options
        self.trending_client = trending_client or GitHubTrendingClient()
        self.progress = progress or (lambda message: None)
        self.validator = QAValidator(strict=options.strict_validation)

    @property
    def output_dir(self) -> Path:
        return self.options.output_dir

    @property
    def clone_dir(self) -> Path:
        return self.output_dir / "repos"

    @property
    def artifact_dir(self) -> Path:
        return self.output_dir / "artifacts"

    @property
    def state_dir(self) -> Path:
        return self.output_dir / "state"

    def run(self) -> list[RepoDigest]:
        """Execute the full configured workflow."""

        repos = self.fetch_trending()
        self.clone_repositories(repos)
        analyses = self.analyze_repositories(repos)
        digests = [RepoDigest(repo=analysis.repo) for analysis in analyses]

        if self.options.mode in {"summarize", "both"}:
            digests = self.generate_summaries(analyses, digests)
        if self.options.mode in {"localize", "both"}:
            digests = self.localize_readmes(analyses, digests)
            digests = self.validate_outputs(digests)

        self._write_json("digests.json", [_digest_to_dict(digest) for digest in digests])
        return digests

    def fetch_trending(self) -> list[TrendingRepo]:
        self._ensure_dirs()
        self.progress(
            f"Fetching {self.options.limit} trending repositories "
            f"for {self.options.language} ({self.options.period})."
        )
        repos = self.trending_client.fetch(
            self.options.language,
            self.options.period,
            self.options.limit,
        )
        if not repos:
            raise WorkflowError("No trending repositories were discovered.")
        selected = repos[: self.options.limit]
        self._write_json("repos.json", [_repo_to_dict(repo) for repo in selected])
        self.progress(f"Fetched {len(selected)} repositories.")
        return selected

    def clone_repositories(self, repos: Sequence[TrendingRepo] | None = None) -> list[Path]:
        self._ensure_dirs()
        repos = list(repos or self.load_repositories())
        paths = []
        for repo in repos:
            destination = self.clone_dir / repo.safe_name
            paths.append(destination)
            if destination.exists():
                self.progress(f"Using existing clone for {repo.slug}.")
                continue
            self.progress(f"Cloning {repo.slug}.")
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo.url, str(destination)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                shutil.rmtree(destination, ignore_errors=True)
                detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
                raise WorkflowError(f"Failed to clone {repo.slug}: {detail}") from exc
        return paths

    def analyze_repositories(
        self, repos: Sequence[TrendingRepo] | None = None
    ) -> list[RepoAnalysis]:
        self._ensure_dirs()
        repos = list(repos or self.load_repositories())
        analyses = []
        for repo in repos:
            self.progress(f"Analyzing README/docs for {repo.slug}.")
            repo_dir = self.clone_dir / repo.safe_name
            if not repo_dir.exists():
                raise WorkflowError(f"Repository has not been cloned: {repo.slug}")
            readme = _find_readme(repo_dir)
            documents = _find_markdown_documents(repo_dir)
            source = readme.read_text(encoding="utf-8", errors="replace") if readme else ""
            analyses.append(
                RepoAnalysis(
                    repo=repo,
                    readme_path=_relative_or_none(readme, self.output_dir),
                    document_paths=[
                        str(path.relative_to(self.output_dir)) for path in documents
                    ],
                    headings=_extract_headings(source),
                    summary_points=_extract_summary_points(source),
                )
            )
        self._write_json("analysis.json", [_analysis_to_dict(item) for item in analyses])
        return analyses

    def generate_summaries(
        self,
        analyses: Sequence[RepoAnalysis] | None = None,
        digests: Sequence[RepoDigest] | None = None,
    ) -> list[RepoDigest]:
        analyses = list(analyses or self.load_analyses())
        by_slug = _digest_map(digests or self._load_digests_if_exists())
        for analysis in analyses:
            self.progress(f"Generating Vietnamese summary for {analysis.repo.slug}.")
            digest = by_slug.setdefault(analysis.repo.slug, RepoDigest(repo=analysis.repo))
            path = self.artifact_dir / analysis.repo.safe_name / "SUMMARY.vi.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_render_summary(analysis), encoding="utf-8")
            digest.summary_path = str(path.relative_to(self.output_dir))
        results = [by_slug[analysis.repo.slug] for analysis in analyses]
        self._write_json("digests.json", [_digest_to_dict(digest) for digest in results])
        return results

    def localize_readmes(
        self,
        analyses: Sequence[RepoAnalysis] | None = None,
        digests: Sequence[RepoDigest] | None = None,
    ) -> list[RepoDigest]:
        analyses = list(analyses or self.load_analyses())
        by_slug = _digest_map(digests or self._load_digests_if_exists())
        for analysis in analyses:
            if analysis.readme_path is None:
                self.progress(f"Skipping localization for {analysis.repo.slug}: no README.")
                continue
            self.progress(f"Creating localized README for {analysis.repo.slug}.")
            digest = by_slug.setdefault(analysis.repo.slug, RepoDigest(repo=analysis.repo))
            source_path = self.output_dir / analysis.readme_path
            source = source_path.read_text(encoding="utf-8", errors="replace")
            destination = self.artifact_dir / analysis.repo.safe_name / "README.vi.md"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(_render_localized_readme(analysis, source), encoding="utf-8")
            digest.localized_readme_path = str(destination.relative_to(self.output_dir))
        results = [by_slug[analysis.repo.slug] for analysis in analyses]
        self._write_json("digests.json", [_digest_to_dict(digest) for digest in results])
        return results

    def validate_outputs(
        self, digests: Sequence[RepoDigest] | None = None
    ) -> list[RepoDigest]:
        digests = list(digests or self.load_digests())
        for digest in digests:
            if digest.localized_readme_path is None:
                continue
            path = self.output_dir / digest.localized_readme_path
            self.progress(f"Validating localized README for {digest.repo.slug}.")
            report = self.validator.validate_file(path)
            digest.validation_report = report.format()
            digest.validation_exit_code = report.exit_code(
                strict=self.options.strict_validation
            )
            if digest.validation_exit_code != 0:
                raise WorkflowError(report.format())
        self._write_json("digests.json", [_digest_to_dict(digest) for digest in digests])
        return digests

    def load_repositories(self) -> list[TrendingRepo]:
        return [_repo_from_dict(item) for item in self._read_json("repos.json")]

    def load_analyses(self) -> list[RepoAnalysis]:
        return [_analysis_from_dict(item) for item in self._read_json("analysis.json")]

    def load_digests(self) -> list[RepoDigest]:
        return [_digest_from_dict(item) for item in self._read_json("digests.json")]

    def _load_digests_if_exists(self) -> list[RepoDigest]:
        path = self.state_dir / "digests.json"
        if not path.exists():
            return []
        return self.load_digests()

    def _ensure_dirs(self) -> None:
        self.clone_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _write_json(self, name: str, payload: object) -> None:
        self._ensure_dirs()
        (self.state_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _read_json(self, name: str) -> object:
        path = self.state_dir / name
        if not path.exists():
            raise WorkflowError(f"Missing workflow state file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))


class _TrendingParser(html.parser.HTMLParser):
    def __init__(self, language: str, limit: int) -> None:
        super().__init__()
        self.language = language
        self.limit = limit
        self.repos: list[TrendingRepo] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a" or len(self.repos) >= self.limit:
            return
        href = dict(attrs).get("href")
        if href is None:
            return
        match = re.fullmatch(r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", href.strip())
        if match is None:
            return
        owner, name = match.groups()
        slug = f"{owner}/{name}"
        if any(repo.slug == slug for repo in self.repos):
            return
        self.repos.append(
            TrendingRepo(
                owner=owner,
                name=name,
                url=f"https://github.com/{slug}.git",
                language=self.language,
            )
        )

    def parse(self, body: str) -> list[TrendingRepo]:
        self.feed(body)
        return self.repos


def _find_readme(repo_dir: Path) -> Path | None:
    candidates = sorted(repo_dir.glob("README*"))
    return next((path for path in candidates if path.is_file()), None)


def _find_markdown_documents(repo_dir: Path) -> list[Path]:
    documents = []
    for pattern in ("*.md", "docs/**/*.md"):
        documents.extend(path for path in repo_dir.glob(pattern) if path.is_file())
    return sorted(set(documents))


def _extract_headings(content: str) -> list[str]:
    headings = []
    for line in content.splitlines():
        match = re.match(r"^#{1,6}\s+(.+)$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings[:8]


def _extract_summary_points(content: str) -> list[str]:
    points = []
    for paragraph in re.split(r"\n\s*\n", content):
        text = " ".join(line.strip() for line in paragraph.splitlines())
        if not text or text.startswith(("#", "```")):
            continue
        points.append(text[:180])
        if len(points) == 3:
            break
    return points


def _render_summary(analysis: RepoAnalysis) -> str:
    points = analysis.summary_points or ["README chưa có phần mô tả đủ rõ để tóm tắt."]
    lines = [
        f"# Tóm tắt {analysis.repo.slug}",
        "",
        f"- Ngôn ngữ xu hướng: {analysis.repo.language or 'không rõ'}.",
        f"- README chính: {analysis.readme_path or 'không tìm thấy'}.",
        f"- Số tài liệu Markdown đã quét: {len(analysis.document_paths)}.",
        "",
        "## Điểm chính",
    ]
    lines.extend(f"- {point}" for point in points)
    lines.append("")
    return "\n".join(lines)


def _render_localized_readme(analysis: RepoAnalysis, source: str) -> str:
    title = analysis.headings[0] if analysis.headings else analysis.repo.slug
    return (
        f"# {title}\n\n"
        f"## Bản địa hóa tiếng Việt\n\n"
        f"Tài liệu này được tạo cho kho `{analysis.repo.slug}` trong quy trình "
        "github-trending-vi-digest. Nội dung gốc được giữ bên dưới để bảo toàn "
        "liên kết, ví dụ mã và thông tin kỹ thuật.\n\n"
        "## Tóm tắt nhanh\n\n"
        + "\n".join(f"- {point}" for point in (analysis.summary_points or ["Chưa có mô tả rõ ràng."]))
        + "\n\n## Nội dung gốc\n\n"
        + source.rstrip()
        + "\n"
    )


def _relative_or_none(path: Path | None, base: Path) -> str | None:
    return str(path.relative_to(base)) if path else None


def _digest_map(digests: Sequence[RepoDigest] | None) -> dict[str, RepoDigest]:
    return {digest.repo.slug: digest for digest in digests or []}


def _repo_to_dict(repo: TrendingRepo) -> dict[str, str | None]:
    return asdict(repo)


def _repo_from_dict(payload: dict[str, str | None]) -> TrendingRepo:
    return TrendingRepo(
        owner=str(payload["owner"]),
        name=str(payload["name"]),
        url=str(payload["url"]),
        language=payload.get("language"),
    )


def _analysis_to_dict(analysis: RepoAnalysis) -> dict[str, object]:
    payload = asdict(analysis)
    payload["repo"] = _repo_to_dict(analysis.repo)
    return payload


def _analysis_from_dict(payload: dict[str, object]) -> RepoAnalysis:
    return RepoAnalysis(
        repo=_repo_from_dict(payload["repo"]),  # type: ignore[arg-type]
        readme_path=payload["readme_path"],  # type: ignore[arg-type]
        document_paths=list(payload["document_paths"]),  # type: ignore[arg-type]
        headings=list(payload["headings"]),  # type: ignore[arg-type]
        summary_points=list(payload["summary_points"]),  # type: ignore[arg-type]
    )


def _digest_to_dict(digest: RepoDigest) -> dict[str, object]:
    payload = asdict(digest)
    payload["repo"] = _repo_to_dict(digest.repo)
    return payload


def _digest_from_dict(payload: dict[str, object]) -> RepoDigest:
    return RepoDigest(
        repo=_repo_from_dict(payload["repo"]),  # type: ignore[arg-type]
        summary_path=payload.get("summary_path"),  # type: ignore[arg-type]
        localized_readme_path=payload.get("localized_readme_path"),  # type: ignore[arg-type]
        validation_report=payload.get("validation_report"),  # type: ignore[arg-type]
        validation_exit_code=payload.get("validation_exit_code"),  # type: ignore[arg-type]
    )
