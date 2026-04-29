import json

from src.validator.language import (
    CharacterEncodingRule,
    CompletenessRule,
    TechnicalTermPreservationRule,
    VietnameseTextRule,
    load_technical_terms,
)


def test_vietnamese_text_rule_detects_untranslated_english_words() -> None:
    content = "Công cụ này will create output files for người dùng."

    result = VietnameseTextRule().validate(content)

    assert result.is_valid is False
    assert "UNTRANSLATED_ENGLISH" in result.errors[0]
    assert "will" in result.errors[0]


def test_vietnamese_text_rule_ignores_code_links_and_allowed_terms() -> None:
    content = (
        "Cài đặt bằng `pip install package` và chạy CLI.\n"
        "Xem thêm tại https://example.com/install"
    )

    result = VietnameseTextRule().validate(content)

    assert result.is_valid is True
    assert result.errors == []


def test_technical_term_rule_reports_missing_preserved_term() -> None:
    source = "Use the GitHub Actions workflow to run pytest."
    localized = "Sử dụng quy trình để chạy pytest."

    result = TechnicalTermPreservationRule(source_content=source).validate(localized)

    assert result.is_valid is False
    assert any("expected 'GitHub Actions'" in error for error in result.errors)


def test_technical_term_rule_reports_translated_technical_term() -> None:
    source = "The SDK exposes a Python API."
    localized = "Bộ phát triển phần mềm cung cấp API Python."

    result = TechnicalTermPreservationRule(source_content=source).validate(localized)

    assert result.is_valid is False
    assert any("TRANSLATED_TECHNICAL_TERM" in error for error in result.errors)
    assert any("expected 'SDK'" in error for error in result.errors)


def test_technical_terms_can_be_loaded_from_json_file(tmp_path) -> None:
    terms_file = tmp_path / "terms.json"
    terms_file.write_text(
        json.dumps({"technical_terms": ["FastAPI"]}),
        encoding="utf-8",
    )

    source = "Start the FastAPI server."
    localized = "Khởi động máy chủ."
    rule = TechnicalTermPreservationRule(
        source_content=source,
        terms_file=terms_file,
    )

    result = rule.validate(localized)

    assert "FastAPI" in load_technical_terms(terms_file)
    assert result.is_valid is False
    assert any("FastAPI" in error for error in result.errors)


def test_completeness_rule_detects_dropped_paragraphs() -> None:
    source = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    localized = "Đoạn đầu tiên."

    result = CompletenessRule(source).validate(localized)

    assert result.is_valid is False
    assert "expected at least 90%" in result.errors[0]
    assert "found 1 translated paragraphs" in result.errors[0]


def test_completeness_rule_accepts_matching_markdown_paragraphs() -> None:
    source = "# Title\n\nUse API.\n\n```bash\npytest\n```\n\nMore details."
    localized = "# Tiêu đề\n\nSử dụng API.\n\n```bash\npytest\n```\n\nThêm chi tiết."

    result = CompletenessRule(source).validate(localized)

    assert result.is_valid is True
    assert result.errors == []


def test_character_encoding_rule_detects_mojibake() -> None:
    content = "TÃ i liệu nÃ y bị lỗi mã hóa."

    result = CharacterEncodingRule().validate(content)

    assert result.is_valid is False
    assert "CORRUPT_VIETNAMESE_ENCODING" in result.errors[0]
    assert "ă, â, ê, ô, ơ, ư, đ" in result.errors[0]


def test_character_encoding_rule_accepts_vietnamese_diacritics() -> None:
    content = "Tài liệu tiếng Việt dùng ă, â, ê, ô, ơ, ư, đ đúng chuẩn UTF-8."

    result = CharacterEncodingRule().validate(content)

    assert result.is_valid is True
    assert result.errors == []
