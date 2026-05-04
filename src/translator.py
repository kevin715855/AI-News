"""Translation helpers for localized README generation."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from collections.abc import Callable

logger = logging.getLogger(__name__)


TranslationClient = Callable[[str, str], str]

_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_URL_RE = re.compile(r"https?://[^\s)>\"]+")
_FILENAME_RE = re.compile(
    r"\b[\w.-]+\.(?:py|md|txt|toml|json|yaml|yml|sh|js|ts|tsx|jsx|css|html)\b"
)


@dataclass
class TranslatorConfig:
    """Configuration for a translation client."""

    target_language: str = "vi"
    preserve_terms: list[str] = field(default_factory=list)
    client: TranslationClient | None = None


class TranslationWrapper:
    """Small wrapper that masks technical Markdown before translation."""

    def __init__(self, config: TranslatorConfig | None = None) -> None:
        self.config = config or TranslatorConfig()

    def translate_text(self, text: str, preserve_patterns: list[str] | None = None) -> str:
        """Translate plain text while preserving configured patterns."""

        if not text:
            return text

        patterns = [
            _URL_RE.pattern,
            _FILENAME_RE.pattern,
            *(preserve_patterns or []),
            *[re.escape(term) for term in self.config.preserve_terms],
        ]
        masked, tokens = _mask_patterns(text, patterns)

        try:
            translated = self._translate(masked)
        except Exception as exc:  # pragma: no cover - exact client exceptions vary
            logger.warning("Translation failed; using original text: %s", exc)
            return text

        return _restore_tokens(translated, tokens)

    def translate_markdown(self, text: str) -> str:
        """Translate Markdown while preserving code, links, URLs, and technical terms."""

        if not text:
            return text

        masked, tokens = _mask_patterns(
            text,
            [
                _FENCED_CODE_RE.pattern,
                _INLINE_CODE_RE.pattern,
                _URL_RE.pattern,
                _FILENAME_RE.pattern,
                *[re.escape(term) for term in self.config.preserve_terms],
            ],
            flags=re.DOTALL,
        )

        try:
            translated = self._translate(masked)
        except Exception as exc:  # pragma: no cover - exact client exceptions vary
            logger.warning("Markdown translation failed; using original Markdown: %s", exc)
            return text

        return _restore_tokens(translated, tokens)

    def _translate(self, text: str) -> str:
        if self.config.client is None:
            return text
        return self.config.client(text, self.config.target_language)


def translate_text(text: str, preserve_patterns: list[str] | None = None) -> str:
    """Translate text to Vietnamese with the default configuration."""

    return TranslationWrapper().translate_text(text, preserve_patterns)


def translate_markdown(text: str) -> str:
    """Translate Markdown to Vietnamese with the default configuration."""

    return TranslationWrapper().translate_markdown(text)


def _mask_patterns(
    text: str,
    patterns: list[str],
    flags: int = 0,
) -> tuple[str, dict[str, str]]:
    tokens: dict[str, str] = {}
    masked = text

    for pattern in patterns:
        regex = re.compile(pattern, flags)

        def replace(match: re.Match[str]) -> str:
            token = f"__PRESERVE_{len(tokens)}__"
            tokens[token] = match.group(0)
            return token

        masked = regex.sub(replace, masked)

    return masked, tokens


def _restore_tokens(text: str, tokens: dict[str, str]) -> str:
    restored = text
    for token, value in tokens.items():
        restored = restored.replace(token, value)
    return restored
