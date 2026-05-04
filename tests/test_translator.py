from translator import TranslationWrapper, TranslatorConfig


def test_translate_markdown_preserves_code_urls_and_terms() -> None:
    def client(text: str, language: str) -> str:
        assert language == "vi"
        return text.replace("Install", "Cai dat").replace("Open docs", "Mo tai lieu")

    translator = TranslationWrapper(
        TranslatorConfig(client=client, preserve_terms=["github-trending-vi-digest"])
    )

    content = """## Install

Run `pip install github-trending-vi-digest`.

```bash
github-trending-vi-digest --help
```

Open docs at https://example.com/docs and README.md.
"""

    translated = translator.translate_markdown(content)

    assert "## Cai dat" in translated
    assert "`pip install github-trending-vi-digest`" in translated
    assert "```bash\ngithub-trending-vi-digest --help\n```" in translated
    assert "https://example.com/docs" in translated
    assert "README.md" in translated


def test_translate_text_falls_back_to_original_on_client_error() -> None:
    def client(text: str, language: str) -> str:
        raise RuntimeError("service unavailable")

    translator = TranslationWrapper(TranslatorConfig(client=client))

    assert translator.translate_text("Hello README.md") == "Hello README.md"
