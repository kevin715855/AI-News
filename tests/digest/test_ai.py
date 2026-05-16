from __future__ import annotations

import json
import urllib.error

import pytest

from digest.ai import AIProviderError, LMStudioConfig, LMStudioProvider, _extract_completion
from digest.editorial import EditorialDigestGenerator


def test_extract_completion_reads_openai_compatible_payload() -> None:
    assert _extract_completion({"choices": [{"message": {"content": "xin chao"}}]}) == "xin chao"


def test_editorial_generator_rejects_invalid_json() -> None:
    class BadProvider:
        def complete(self, prompt: str) -> str:
            return "khong phai json"

    with pytest.raises(AIProviderError):
        EditorialDigestGenerator(BadProvider()).generate("octo/demo", "# Demo")


def test_editorial_generator_reads_tagged_blocks() -> None:
    class GoodProvider:
        def complete(self, prompt: str) -> str:
            return """
<summary>Một công cụ hữu ích.</summary>
<highlights>
- Nhanh.
- Rõ.
</highlights>
<why_it_matters>Giúp làm việc gọn hơn.</why_it_matters>
<localized_readme># Demo

Đây là README tiếng Việt.
</localized_readme>
""".strip()

    digest = EditorialDigestGenerator(GoodProvider()).generate("octo/demo", "# Demo")

    assert digest.summary == "Một công cụ hữu ích."
    assert digest.highlights == ("Nhanh.", "Rõ.")


def test_editorial_generator_repairs_bad_first_response() -> None:
    class RepairingProvider:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, prompt: str) -> str:
            self.calls += 1
            if self.calls == 1:
                return "summary: mot cong cu"
            return """
<summary>Một công cụ hữu ích.</summary>
<highlights>
- Nhanh.
</highlights>
<why_it_matters>Giúp làm việc gọn hơn.</why_it_matters>
<localized_readme># Demo</localized_readme>
""".strip()

    provider = RepairingProvider()
    digest = EditorialDigestGenerator(provider).generate("octo/demo", "# Demo")

    assert provider.calls == 2
    assert digest.summary == "Một công cụ hữu ích."


def test_editorial_generator_accepts_unclosed_final_localized_readme_block() -> None:
    class Provider:
        def complete(self, prompt: str) -> str:
            return """
<summary>Một công cụ hữu ích.</summary>
<highlights>
- Nhanh.
</highlights>
<why_it_matters>Giúp làm việc gọn hơn.</why_it_matters>
<localized_readme># Demo

Đây là README tiếng Việt.
""".strip()

    digest = EditorialDigestGenerator(Provider()).generate("octo/demo", "# Demo")

    assert "README tiếng Việt" in digest.localized_readme


def test_lmstudio_provider_reports_actionable_error(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    provider = LMStudioProvider(LMStudioConfig(retries=0))

    with pytest.raises(AIProviderError) as exc_info:
        provider.complete("hello")

    assert "LM Studio" in str(exc_info.value)


def test_lmstudio_provider_handles_timeout(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise TimeoutError("slow")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    provider = LMStudioProvider(LMStudioConfig(retries=0))

    with pytest.raises(AIProviderError):
        provider.complete("hello")
