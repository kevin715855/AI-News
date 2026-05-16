"""Editorial digest generation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .ai import AIProvider, AIProviderError


@dataclass(frozen=True)
class EditorialDigest:
    """Structured Vietnamese digest content for one repository."""

    summary: str
    highlights: tuple[str, ...]
    why_it_matters: str
    localized_readme: str


class EditorialDigestGenerator:
    """Generate reader-facing Vietnamese digest content from README Markdown."""

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def generate(self, repo_slug: str, source_markdown: str) -> EditorialDigest:
        response = self.provider.complete(_build_prompt(repo_slug, source_markdown))
        try:
            return _parse_digest(response)
        except ValueError:
            repaired = self.provider.complete(_build_repair_prompt(response))
            try:
                return _parse_digest(repaired)
            except ValueError as exc:
                raise AIProviderError(
                    "Model trả về dữ liệu không đúng định dạng digest đã yêu cầu."
                ) from exc


def _parse_digest(response: str) -> EditorialDigest:
        try:
            summary = _extract_block(response, "summary")
            highlights = _extract_highlights(_extract_block(response, "highlights"))
            why_it_matters = _extract_block(response, "why_it_matters")
            localized_readme = _extract_block(response, "localized_readme")
        except ValueError:
            raise
        return EditorialDigest(
            summary=summary,
            highlights=tuple(highlights),
            why_it_matters=why_it_matters,
            localized_readme=localized_readme,
        )


def _build_prompt(repo_slug: str, source_markdown: str) -> str:
    return f"""
Bạn là một biên tập viên công nghệ viết tiếng Việt cho độc giả muốn hiểu nhanh
một repository trước khi quyết định có nên dành thời gian cho nó hay không.

Hãy tạo digest cho repository `{repo_slug}`.

Chuẩn biên tập:
- Viết tự nhiên như một bản tin công nghệ ngắn, không dịch sát từng câu.
- Nêu rõ vấn đề repo giải quyết, cách nó tạo khác biệt, và vì sao điều đó đáng quan tâm.
- Ưu tiên câu gọn, sáng, giàu thông tin; tránh văn quảng cáo và tránh lặp lại ý.
- Dùng tiếng Việt nhất quán cho phần văn xuôi và tiêu đề; không để sót câu ngoại ngữ lạc giọng.
- Giữ nguyên code block, lệnh, URL, tên file, package name, CLI flag, API name và tên sản phẩm kỹ thuật.

Định dạng trả về:
- Chỉ trả về đúng 4 khối theo thứ tự này, không thêm lời mở đầu hay kết luận:
  <summary>...</summary>
  <highlights>
  - ...
  - ...
  </highlights>
  <why_it_matters>...</why_it_matters>
  <localized_readme>...</localized_readme>
- summary: 2-3 câu, giúp người đọc hiểu repo làm gì và lợi ích chính là gì.
- highlights: 3-5 ý, mỗi ý là một câu hoàn chỉnh, ưu tiên insight hơn là danh sách tính năng rời rạc.
- why_it_matters: 2-3 câu, giải thích repo này quan trọng với ai và trong bối cảnh nào.
- localized_readme: bản README tiếng Việt cô đọng trong khoảng 250-350 từ, theo nhịp:
  1. một đoạn mở ngắn,
  2. mục `### Điểm chính` với 3-5 gạch đầu dòng,
  3. mục `### Bắt đầu nhanh` có ít nhất một code block thực tế nếu README nguồn có lệnh cài đặt/chạy,
  4. tối đa một đoạn kết ngắn nếu thật sự cần.
- Có thể lược bớt phần lặp và danh sách quá dài nhưng không được bóp méo ý kỹ thuật.
- Luôn đóng đầy đủ cả 4 thẻ, kể cả khi cần rút ngắn nội dung để làm điều đó.

README gốc:
{source_markdown}
""".strip()


def _build_repair_prompt(response: str) -> str:
    return f"""
Hãy chỉ sửa định dạng của câu trả lời sau.

Yêu cầu bắt buộc:
- Không viết thêm lời giải thích.
- Không đổi ý nghĩa nội dung nếu không cần thiết.
- Chỉ trả về đúng 4 khối:
  <summary>...</summary>
  <highlights>
  - ...
  </highlights>
  <why_it_matters>...</why_it_matters>
  <localized_readme>...</localized_readme>
- Luôn đóng đầy đủ cả 4 thẻ.

Câu trả lời cần sửa:
{response}
""".strip()


def _extract_block(response: str, tag: str) -> str:
    match = re.search(fr"<{tag}>\s*(.*?)\s*</{tag}>", response, flags=re.DOTALL)
    if match is None and tag == "localized_readme":
        fallback = re.search(fr"<{tag}>\s*(.*)\Z", response, flags=re.DOTALL)
        if fallback is not None:
            content = fallback.group(1).strip()
        else:
            raise ValueError(tag)
    elif match is None:
        raise ValueError(tag)
    else:
        content = match.group(1).strip()
    if not content:
        raise ValueError(tag)
    return content


def _extract_highlights(block: str) -> list[str]:
    items = [
        line.strip()[2:].strip()
        for line in block.splitlines()
        if line.strip().startswith("- ")
    ]
    if not items:
        raise ValueError("highlights")
    return items[:5]
