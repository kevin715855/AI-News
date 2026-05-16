from __future__ import annotations

from pathlib import Path

from digest.workflow import DigestWorkflow, TrendingRepo, WorkflowOptions
from digest.workflow import _normalize_nested_headings, _repair_heading_hierarchy


class FakeProvider:
    def complete(self, prompt: str) -> str:
        return """
<summary>Đây là một công cụ demo giúp kiểm thử workflow.</summary>
<highlights>
- Có CLI rõ ràng.
- Giữ nguyên code block.
- Phù hợp để tạo digest tiếng Việt.
</highlights>
<why_it_matters>Người đọc hiểu nhanh repo mà không cần mở README gốc.</why_it_matters>
<localized_readme># Demo

Đây là README tiếng Việt.

```bash
pytest
```</localized_readme>
""".strip()


def test_prepare_repository_url_normalizes_github_urls(tmp_path: Path) -> None:
    workflow = DigestWorkflow(WorkflowOptions(output_dir=tmp_path), ai_provider=FakeProvider())

    repos = workflow.prepare_repository_url("https://github.com/octo/demo")

    assert repos[0] == TrendingRepo("octo", "demo", "https://github.com/octo/demo.git")


def test_generate_markdown_outputs_writes_reader_facing_digest(tmp_path: Path) -> None:
    repo = TrendingRepo("octo", "demo", "https://example.com/octo/demo.git", "python")
    workflow = DigestWorkflow(WorkflowOptions(output_dir=tmp_path), ai_provider=FakeProvider())
    local_repo = workflow.clone_dir / repo.safe_name
    local_repo.mkdir(parents=True)
    (local_repo / "README.md").write_text("# Demo\n\nA demo repo.\n", encoding="utf-8")
    analyses = workflow.analyze_repositories([repo])

    digests = workflow.generate_markdown_outputs(analyses)

    assert digests[0].markdown_path == "artifacts\\octo__demo\\DIGEST.vi.md"
    content = (tmp_path / digests[0].markdown_path).read_text(encoding="utf-8")
    assert "Đây là một công cụ demo giúp kiểm thử workflow." in content
    assert "## Điều đáng chú ý" in content
    assert "## Vì sao repo này đáng để mở" in content
    assert "Đây là README tiếng Việt." in content


def test_normalize_nested_headings_demotes_inner_titles() -> None:
    content = _normalize_nested_headings("# Demo\n\n### Bắt đầu")

    assert content.splitlines() == ["### Demo", "", "### Bắt đầu"]


def test_repair_heading_hierarchy_closes_level_gaps() -> None:
    content = _repair_heading_hierarchy("# Demo\n\n#### Bắt đầu")

    assert content.splitlines() == ["# Demo", "", "## Bắt đầu"]
