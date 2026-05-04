from github_trending_vi_digest import (
    DocumentExtractor,
    DocumentExtractorConfig,
    RepositoryFile,
    RepositorySnapshot,
    extract_documents,
)
import pytest


def _snapshot(files: list[RepositoryFile]) -> RepositorySnapshot:
    return RepositorySnapshot.from_files("kevin715855/AI-News", files)


def test_readme_is_ranked_before_other_docs() -> None:
    snapshot = _snapshot(
        [
            RepositoryFile("docs/setup.md", "# Setup\n\nDetailed setup guide for contributors."),
            RepositoryFile(
                "README.md",
                "# Project\n\nThis is the main entry point for readers and contributors.",
            ),
            RepositoryFile("src/app.py", "print('hello')"),
        ]
    )

    docs = extract_documents(snapshot, max_documents=2)

    assert docs
    assert docs[0].path == "README.md"


def test_markdown_headings_are_split_into_sections() -> None:
    snapshot = _snapshot(
        [
            RepositoryFile(
                "README.md",
                "# Overview\n\nA project intro.\n\n## Installation\n\nRun setup commands.",
            )
        ]
    )
    extractor = DocumentExtractor(
        DocumentExtractorConfig(max_documents=5, min_characters=1)
    )

    docs = extractor.extract(snapshot)

    assert [doc.title for doc in docs] == ["Overview", "Installation"]


def test_binary_and_short_files_are_skipped() -> None:
    snapshot = _snapshot(
        [
            RepositoryFile("README.md", "# Overview\n\nLong enough meaningful content."),
            RepositoryFile("docs/logo.md", "\x00PNG"),
            RepositoryFile("docs/notes.txt", "tiny"),
        ]
    )

    docs = DocumentExtractor().extract(snapshot)

    assert len(docs) == 1
    assert docs[0].path == "README.md"


def test_limits_document_count_and_character_size() -> None:
    snapshot = _snapshot(
        [
            RepositoryFile(
                "README.md",
                "# One\n\nabcdefghijklmno\n\n## Two\n\npqrstuvwxyzabcd\n\n## Three\n\nefghijklmnop",
            )
        ]
    )
    extractor = DocumentExtractor(
        DocumentExtractorConfig(
            max_documents=2,
            max_characters_per_document=20,
            min_characters=1,
        )
    )

    docs = extractor.extract(snapshot)

    assert len(docs) == 2
    assert all(len(doc.content) <= 20 for doc in docs)


def test_invalid_limits_raise_value_error() -> None:
    with pytest.raises(ValueError):
        DocumentExtractorConfig(max_documents=0)

    with pytest.raises(ValueError):
        DocumentExtractorConfig(max_characters_per_document=0)
