"""Vietnamese language validation rules for localized README content."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable

from .base import ValidationError, ValidationResult, ValidationRule
from .terms import DEFAULT_TECHNICAL_TERMS, DEFAULT_TRANSLATED_TECHNICAL_TERMS

VIETNAMESE_CHARS = set(
    "ăâêôơưđ"
    "áàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩị"
    "óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
)
VIETNAMESE_MARKERS = {
    "các",
    "của",
    "cho",
    "được",
    "không",
    "là",
    "một",
    "người",
    "này",
    "trong",
    "và",
    "với",
}
COMMON_ENGLISH_WORDS = {
    "the",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "with",
    "from",
    "this",
    "that",
    "these",
    "those",
    "use",
    "uses",
    "using",
    "will",
    "create",
    "creates",
    "install",
    "run",
    "build",
    "configure",
    "configuration",
    "generate",
    "output",
    "input",
    "file",
    "files",
    "repository",
    "translation",
    "read",
    "write",
    "returns",
    "error",
}
MOJIBAKE_MARKERS = ("�", "Ã", "Â", "Ä", "Æ", "Ð", "ð", "ï¿½")


class VietnameseTextRule(ValidationRule):
    """Detect likely untranslated English artifacts in Vietnamese prose."""

    name = "vietnamese_text"

    def __init__(
        self,
        allowed_english_terms: Iterable[str] | None = None,
        terms_file: str | Path | None = None,
        max_english_words_per_line: int = 2,
    ) -> None:
        self.allowed_english_terms = {
            term.lower()
            for term in load_technical_terms(terms_file, allowed_english_terms)
        }
        self.max_english_words_per_line = max_english_words_per_line

    def validate(self, content: str) -> ValidationResult:
        result = ValidationResult.valid()
        for line_number, line in enumerate(_strip_markdown_code(content).splitlines(), 1):
            if not _looks_like_vietnamese_sentence(line):
                continue

            english_words = [
                word
                for word in _english_words(line)
                if word.lower() not in self.allowed_english_terms
                and word.lower() in COMMON_ENGLISH_WORDS
            ]
            if len(english_words) > self.max_english_words_per_line:
                result.add_error(
                    ValidationError(
                        rule_name=self.rule_name,
                        code="UNTRANSLATED_ENGLISH",
                        line=line_number,
                        message=(
                            "Vietnamese sentence contains likely untranslated English "
                            f"words: expected Vietnamese prose, found {english_words}"
                        ),
                    )
                )
        return result


class TechnicalTermPreservationRule(ValidationRule):
    """Ensure configured technical terms remain in English."""

    name = "technical_term_preservation"

    def __init__(
        self,
        source_content: str = "",
        terms: Iterable[str] | None = None,
        terms_file: str | Path | None = None,
        translated_terms: dict[str, Iterable[str]] | None = None,
    ) -> None:
        self.source_content = source_content
        self.terms = load_technical_terms(terms_file, terms)
        self.translated_terms = {
            term: list(values)
            for term, values in DEFAULT_TRANSLATED_TECHNICAL_TERMS.items()
        }
        if translated_terms:
            self.translated_terms.update(
                {term: list(values) for term, values in translated_terms.items()}
            )

    def validate(self, content: str) -> ValidationResult:
        result = ValidationResult.valid()
        comparable_source = _strip_markdown_code(self.source_content)
        comparable_target = _strip_markdown_code(content)

        for term in self.terms:
            if self.source_content and not _contains_term(comparable_source, term):
                continue

            if self.source_content and not _contains_term(comparable_target, term):
                result.add_error(
                    ValidationError(
                        rule_name=self.rule_name,
                        code="MISSING_TECHNICAL_TERM",
                        message=(
                            f"Technical term was not preserved: expected '{term}' "
                            "from source content to appear unchanged in translation"
                        ),
                    )
                )

            for translated in self.translated_terms.get(term, []):
                line = _line_number_for(comparable_target, translated)
                if line is not None:
                    result.add_error(
                        ValidationError(
                            rule_name=self.rule_name,
                            code="TRANSLATED_TECHNICAL_TERM",
                            line=line,
                            message=(
                                f"Technical term appears translated: expected '{term}', "
                                f"found '{translated}'"
                            ),
                        )
                    )
        return result


class CompletenessRule(ValidationRule):
    """Verify source paragraphs have corresponding translated paragraphs."""

    name = "completeness"

    def __init__(self, source_content: str, minimum_ratio: float = 0.9) -> None:
        self.source_content = source_content
        self.minimum_ratio = minimum_ratio

    def validate(self, content: str) -> ValidationResult:
        result = ValidationResult.valid()
        source_paragraphs = _paragraphs(self.source_content)
        target_paragraphs = _paragraphs(content)
        if not source_paragraphs:
            return result

        ratio = len(target_paragraphs) / len(source_paragraphs)
        if ratio < self.minimum_ratio:
            result.add_error(
                ValidationError(
                    rule_name=self.rule_name,
                    code="DROPPED_PARAGRAPHS",
                    message=(
                        "Translation appears incomplete: expected at least "
                        f"{self.minimum_ratio:.0%} paragraph coverage "
                        f"({len(source_paragraphs)} source paragraphs), "
                        f"found {len(target_paragraphs)} translated paragraphs "
                        f"({ratio:.0%})"
                    ),
                )
            )
        return result


class CharacterEncodingRule(ValidationRule):
    """Validate UTF-8 text and Vietnamese diacritics are not corrupted."""

    name = "character_encoding"

    def validate(self, content: str) -> ValidationResult:
        result = ValidationResult.valid()

        try:
            content.encode("utf-8").decode("utf-8")
        except UnicodeError as exc:
            result.add_error(
                ValidationError(
                    rule_name=self.rule_name,
                    code="INVALID_UTF8",
                    message=f"Content is not valid UTF-8: {exc}",
                )
            )

        for marker in MOJIBAKE_MARKERS:
            line = _line_number_for(content, marker, ignore_case=False)
            if line is not None:
                result.add_error(
                    ValidationError(
                        rule_name=self.rule_name,
                        code="CORRUPT_VIETNAMESE_ENCODING",
                        line=line,
                        message=(
                            "Content contains likely mojibake or replacement "
                            f"characters: found '{marker}', expected valid UTF-8 "
                            "Vietnamese diacritics such as ă, â, ê, ô, ơ, ư, đ"
                        ),
                    )
                )

        normalized = unicodedata.normalize("NFC", content)
        if normalized != content:
            result.add_warning(
                ValidationError(
                    rule_name=self.rule_name,
                    code="NON_NORMALIZED_UNICODE",
                    message="Content should be normalized to NFC for Vietnamese text",
                )
            )
        return result


def load_technical_terms(
    terms_file: str | Path | None = None,
    extra_terms: Iterable[str] | None = None,
) -> list[str]:
    """Load preserved terms from defaults, a JSON/text file, and overrides."""

    terms = list(DEFAULT_TECHNICAL_TERMS)
    if terms_file:
        path = Path(terms_file)
        raw = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            data = json.loads(raw)
            if isinstance(data, dict):
                configured = (
                    data.get("technical_terms")
                    or data.get("preserve_terms")
                    or data.get("terms")
                    or []
                )
            else:
                configured = data
            terms.extend(str(term) for term in configured)
        else:
            terms.extend(
                line.strip()
                for line in raw.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
    if extra_terms:
        terms.extend(str(term) for term in extra_terms)
    return sorted(set(terms), key=str.lower)


def _strip_markdown_code(content: str) -> str:
    without_fences = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    without_inline = re.sub(r"`[^`\n]+`", "", without_fences)
    return re.sub(r"https?://\S+", "", without_inline)


def _looks_like_vietnamese_sentence(line: str) -> bool:
    lowered = line.lower()
    words = set(re.findall(r"\b\w+\b", lowered, flags=re.UNICODE))
    return bool(VIETNAMESE_CHARS.intersection(lowered)) or bool(
        words.intersection(VIETNAMESE_MARKERS)
    )


def _english_words(line: str) -> list[str]:
    return re.findall(r"\b[A-Za-z][A-Za-z-]*\b", line)


def _contains_term(content: str, term: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", content, re.IGNORECASE) is not None


def _line_number_for(
    content: str,
    needle: str,
    ignore_case: bool = True,
) -> int | None:
    normalized_needle = needle.lower() if ignore_case else needle
    for line_number, line in enumerate(content.splitlines(), 1):
        comparable_line = line.lower() if ignore_case else line
        if normalized_needle in comparable_line:
            return line_number
    return None


def _paragraphs(content: str) -> list[str]:
    cleaned = _strip_markdown_code(content)
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", cleaned):
        normalized = "\n".join(
            line.strip()
            for line in paragraph.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", ">", "|"))
        ).strip()
        if normalized:
            paragraphs.append(normalized)
    return paragraphs
