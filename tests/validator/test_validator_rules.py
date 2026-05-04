from validator import (
    CodeBlockPreservationRule,
    HeadingHierarchyRule,
    LinkIntegrityRule,
    MarkdownStructureRule,
    Validator,
)


def test_markdown_structure_detects_unbalanced_backtick_fence() -> None:
    result = MarkdownStructureRule().validate("# README\n\n```python\nprint('hello')\n")

    assert result.is_valid is False
    assert "line 3" in result.errors[0]
    assert "Unclosed" in result.errors[0]


def test_code_block_preservation_reports_missing_source_block() -> None:
    source = "# Tool\n\n```bash\npython -m ai_news\n```\n"
    localized = "# Cong cu\n\n```bash\npython -m renamed\n```\n"

    result = CodeBlockPreservationRule().validate(localized, source_content=source)

    assert result.is_valid is False
    assert "MISSING_CODE_BLOCK" in result.errors[0]
    assert "line 3" in result.errors[0]


def test_code_block_preservation_allows_no_source_blocks_and_preserved_blocks() -> None:
    rule = CodeBlockPreservationRule()
    assert rule.validate("# Xin chao", source_content="# Hello").is_valid

    source = "```js\nconsole.log('same')\n```\n"
    localized = "Mo ta\n\n```js\nconsole.log('same')\n```\n"

    assert rule.validate(localized, source_content=source).is_valid


def test_link_integrity_requires_source_links_to_be_unchanged() -> None:
    source = "[Docs](https://example.com/docs) and ![Logo](assets/logo.png)"
    localized = "[Tai lieu](https://example.com/vi/docs) and ![Logo](assets/logo.png)"

    result = LinkIntegrityRule().validate(localized, source_content=source)

    assert result.is_valid is False
    assert "https://example.com/docs" in result.errors[0]


def test_link_integrity_flags_invalid_absolute_url() -> None:
    result = LinkIntegrityRule().validate("[Bad](https://localhost/path)")

    assert result.is_valid is False
    assert "INVALID_LINK_TARGET" in result.errors[0]


def test_heading_hierarchy_detects_skipped_levels() -> None:
    result = HeadingHierarchyRule().validate("# Title\n### Details\n")

    assert result.is_valid is False
    assert "line 2" in result.errors[0]
    assert "h1 to h3" in result.errors[0]


def test_rules_integrate_with_validator_runner_source_content() -> None:
    source = "# Title\n\n```bash\necho ok\n```\n[Docs](https://example.com/docs)"
    localized = "# Tieu de\n### Bo qua\n```bash\necho changed\n```\n[Docs](https://other.example.com)"
    validator = Validator(
        [
            MarkdownStructureRule(),
            CodeBlockPreservationRule(),
            LinkIntegrityRule(),
            HeadingHierarchyRule(),
        ]
    )

    result = validator.validate(localized, source_content=source)

    assert result.is_valid is False
    assert any("code-block-preservation" in error for error in result.errors)
    assert any("link-integrity" in error for error in result.errors)
    assert any("heading-hierarchy" in error for error in result.errors)
