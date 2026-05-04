from pathlib import Path

from localizer import READMELocalizer


class FakeVietnameseTranslator:
    def translate_markdown(self, text: str) -> str:
        replacements = {
            "Project": "Du an",
            "Install": "Cai dat",
            "Usage": "Su dung",
            "Run": "Chay",
            "Read more": "Doc them",
            "Option": "Tuy chon",
            "Description": "Mo ta",
        }
        translated = text
        for source, target in replacements.items():
            translated = translated.replace(source, target)
        return translated


def test_readme_localization_preserves_markdown_code_and_urls(tmp_path: Path) -> None:
    readme = """# Project

Read more at https://example.com/docs.

## Install

Run `pip install github-trending-vi-digest`.

```bash
github-trending-vi-digest --language vi
```

See [local config](docs/config.md).
"""
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")

    result = READMELocalizer(translator=FakeVietnameseTranslator()).localize(tmp_path)

    localized = result.output_path.read_text(encoding="utf-8")
    assert "# Du an" in localized
    assert "## Cai dat" in localized
    assert "https://example.com/docs" in localized
    assert "`pip install github-trending-vi-digest`" in localized
    assert "```bash\ngithub-trending-vi-digest --language vi\n```" in localized
    assert result.metadata["source_file_references"] == ["docs/config.md"]


def test_readme_localization_handles_tables_without_external_calls(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """# Project

| Option | Description |
| --- | --- |
| `--language` | Output language |
""",
        encoding="utf-8",
    )

    result = READMELocalizer(translator=FakeVietnameseTranslator()).localize(tmp_path)

    localized = result.vietnamese_content
    assert "| Tuy chon | Mo ta |" in localized
    assert "| `--language` | Output language |" in localized
    assert result.output_path.exists()
    assert result.metadata_path.exists()
