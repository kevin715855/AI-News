from pathlib import Path

from digest.cli import main
from digest.workflow import DigestWorkflow, TrendingRepo, WorkflowOptions


class FakeTrendingClient:
    def __init__(self, repos: list[TrendingRepo]) -> None:
        self.repos = repos

    def fetch(self, language: str, period: str, limit: int) -> list[TrendingRepo]:
        return self.repos[:limit]


def test_full_workflow_generates_summary_localized_readme_and_validation(
    tmp_path: Path,
) -> None:
    repo = TrendingRepo("octo", "demo", "https://example.com/octo/demo.git", "python")
    workflow = DigestWorkflow(
        WorkflowOptions(output_dir=tmp_path, limit=1),
        trending_client=FakeTrendingClient([repo]),
    )
    local_repo = workflow.clone_dir / repo.safe_name
    local_repo.mkdir(parents=True)
    (local_repo / "README.md").write_text(
        "# Demo\n\nA small CLI for testing.\n\n```bash\npytest\n```\n",
        encoding="utf-8",
    )

    digests = workflow.run()

    assert len(digests) == 1
    assert digests[0].summary_path == "artifacts\\octo__demo\\SUMMARY.vi.md"
    assert digests[0].localized_readme_path == "artifacts\\octo__demo\\README.vi.md"
    assert digests[0].validation_exit_code == 0
    assert (tmp_path / digests[0].summary_path).exists()
    localized = (tmp_path / digests[0].localized_readme_path).read_text(encoding="utf-8")
    assert "Bản địa hóa tiếng Việt" in localized
    assert "```bash\npytest\n```" in localized


def test_cli_supports_individual_steps_with_saved_state(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo = TrendingRepo("octo", "step-demo", "https://example.com/octo/step-demo.git", "go")

    def fake_client():
        return FakeTrendingClient([repo])

    monkeypatch.setattr("digest.workflow.GitHubTrendingClient", fake_client)

    assert main(["--language", "go", "--limit", "1", "--output-dir", str(tmp_path), "fetch"]) == 0
    local_repo = tmp_path / "repos" / repo.safe_name
    local_repo.mkdir(parents=True)
    (local_repo / "README.md").write_text("# Step Demo\n\nRun it locally.\n", encoding="utf-8")

    assert main(["--output-dir", str(tmp_path), "analyze"]) == 0
    assert main(["--output-dir", str(tmp_path), "summarize"]) == 0
    assert main(["--output-dir", str(tmp_path), "localize"]) == 0
    assert main(["--output-dir", str(tmp_path), "validate"]) == 0

    output = capsys.readouterr().out
    assert "[digest]" in output
    assert (tmp_path / "artifacts" / repo.safe_name / "SUMMARY.vi.md").exists()
    assert (tmp_path / "artifacts" / repo.safe_name / "README.vi.md").exists()
