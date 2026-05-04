from pathlib import Path

import pytest

from localizer import LocalizerError, READMELocalizer


class FakeTranslator:
    def translate_markdown(self, text: str) -> str:
        return text.replace("Project", "Du an").replace("Install", "Cai dat")


def test_localizer_writes_vietnamese_readme_and_metadata(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# Project\n\nSee [config](docs/config.md).\n\n## Install\n",
        encoding="utf-8",
    )

    result = READMELocalizer(translator=FakeTranslator()).localize(tmp_path)

    assert result.output_path == tmp_path / "localized" / "README.vi.md"
    assert result.output_path.read_text(encoding="utf-8").startswith("# Du an")
    assert result.metadata["source_readme"] == "README.md"
    assert result.metadata["source_file_references"] == ["docs/config.md"]
    assert result.metadata_path.exists()


def test_localizer_raises_for_missing_readme(tmp_path: Path) -> None:
    with pytest.raises(LocalizerError, match="No README"):
        READMELocalizer(translator=FakeTranslator()).localize(tmp_path)
