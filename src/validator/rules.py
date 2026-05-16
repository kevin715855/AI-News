"""Default README QA validation rules."""

from __future__ import annotations

import re

from dataclasses import dataclass

from .base import ValidationError, ValidationResult, ValidationRule
from .config import ValidationSeverity


@dataclass(frozen=True)
class CodeBlock:
    body: str
    start_line: int

    @property
    def normalized_body(self) -> str:
        return self.body.strip("\n\r")


class MarkdownStructureRule(ValidationRule):
    """Validate basic Markdown structure that commonly breaks localization output."""

    name = "markdown-structure"

    def validate(
        self,
        content: str,
        source_content: str | None = None,
    ) -> ValidationResult:
        result = ValidationResult.valid()
        fence_line = None
        for line_number, line in enumerate(content.splitlines(), start=1):
            if line.lstrip().startswith("```"):
                fence_line = line_number if fence_line is None else None

        if fence_line is not None:
            result.add_error(
                ValidationError(
                    self.rule_name,
                    "Unclosed fenced code block.",
                    line=fence_line,
                    code="UNCLOSED_CODE_FENCE",
                )
            )
        return result


class CodeBlockPreservationRule(ValidationRule):
    """Verify fenced code blocks from the source remain unchanged."""

    name = "code-block-preservation"

    def validate(
        self,
        content: str,
        source_content: str | None = None,
    ) -> ValidationResult:
        result = ValidationResult.valid()
        if source_content is None:
            return result

        localized_bodies = {
            block.normalized_body for block in _extract_code_blocks(content)
        }
        for block in _extract_code_blocks(source_content):
            if block.normalized_body not in localized_bodies:
                result.add_error(
                    ValidationError(
                        self.rule_name,
                        "Source code block is missing from localized content.",
                        line=block.start_line,
                        code="MISSING_CODE_BLOCK",
                    )
                )
        return result


class HeadingHierarchyRule(ValidationRule):
    """Ensure heading levels do not skip structural levels."""

    name = "heading-hierarchy"

    def validate(
        self,
        content: str,
        source_content: str | None = None,
    ) -> ValidationResult:
        result = ValidationResult.valid()
        previous_level = 0
        in_fence = False
        for line_number, line in enumerate(content.splitlines(), start=1):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            match = re.match(r"^(#{1,6})\s+\S", line)
            if not match:
                continue

            level = len(match.group(1))
            if previous_level and level > previous_level + 1:
                result.add_error(
                    ValidationError(
                        self.rule_name,
                        f"Heading jumps from h{previous_level} to h{level}.",
                        line=line_number,
                        code="HEADING_LEVEL_SKIP",
                    )
                )
            previous_level = level
        return result


class LinkIntegrityRule(ValidationRule):
    """Check localized Markdown links and preserve source targets when provided."""

    name = "link-integrity"

    def validate(
        self,
        content: str,
        source_content: str | None = None,
    ) -> ValidationResult:
        result = ValidationResult.valid()
        localized_targets = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            for match in re.finditer(r"!?\[[^\]]+\]\(([^)]*)\)", line):
                target = match.group(1).strip()
                localized_targets.append(target)
                if not target:
                    result.add_error(
                        ValidationError(
                            self.rule_name,
                            "Markdown link has an empty target.",
                            line=line_number,
                            column=match.start(1) + 1,
                            code="EMPTY_LINK_TARGET",
                        )
                    )
                elif target.startswith(("http://", "https://")) and "." not in target.split("://", 1)[1].split("/", 1)[0]:
                    result.add_error(
                        ValidationError(
                            self.rule_name,
                            f"Invalid markdown link target: {target}.",
                            line=line_number,
                            column=match.start(1) + 1,
                            code="INVALID_LINK_TARGET",
                        )
                    )
                elif re.search(r"\s", target):
                    result.add_warning(
                        ValidationError(
                            self.rule_name,
                            "Markdown link target contains whitespace.",
                            severity=ValidationSeverity.WARNING,
                            line=line_number,
                            column=match.start(1) + 1,
                            code="LINK_TARGET_WHITESPACE",
                        )
                    )
        if source_content is not None:
            for line_number, line in enumerate(source_content.splitlines(), start=1):
                for match in re.finditer(r"!?\[[^\]]+\]\(([^)]*)\)", line):
                    target = match.group(1).strip()
                    if target and target not in localized_targets:
                        result.add_error(
                            ValidationError(
                                self.rule_name,
                                f"Source link target was not preserved unchanged: {target}.",
                                line=line_number,
                                code="MISSING_SOURCE_LINK",
                            )
                        )
        return result


class VietnameseLocalizationRule(ValidationRule):
    """Warn when localized content does not appear to contain Vietnamese prose."""

    name = "vietnamese-localization"
    severity = ValidationSeverity.WARNING
    _vietnamese_pattern = re.compile(
        r"[ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩị"
        r"óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
        re.IGNORECASE,
    )

    def validate(
        self,
        content: str,
        source_content: str | None = None,
    ) -> ValidationResult:
        result = ValidationResult.valid()
        prose = "\n".join(
            line
            for line in content.splitlines()
            if line.strip() and not line.lstrip().startswith(("```", "#", "-", "*"))
        )
        if prose and not self._vietnamese_pattern.search(prose):
            result.add_warning(
                ValidationError(
                    self.rule_name,
                    "Localized README prose does not contain Vietnamese diacritics.",
                    severity=ValidationSeverity.WARNING,
                    line=1,
                    code="NO_VIETNAMESE_DIACRITICS",
                )
            )
        return result


def _extract_code_blocks(content: str) -> list[CodeBlock]:
    blocks = []
    active_start = None
    active_marker = None
    body_lines = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if active_start is None:
                active_start = line_number
                active_marker = marker
                body_lines = []
            elif marker == active_marker:
                blocks.append(CodeBlock("\n".join(body_lines), active_start))
                active_start = None
                active_marker = None
                body_lines = []
            else:
                body_lines.append(line)
        elif active_start is not None:
            body_lines.append(line)
    return blocks


def default_rules() -> list[ValidationRule]:
    """Return the default localized README validation rule set."""

    return [
        MarkdownStructureRule(),
        CodeBlockPreservationRule(),
        HeadingHierarchyRule(),
        LinkIntegrityRule(),
        VietnameseLocalizationRule(),
    ]
