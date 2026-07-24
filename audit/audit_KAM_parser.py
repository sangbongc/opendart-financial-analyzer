from bs4 import Tag, BeautifulSoup
import re
from audit.models import (
    KeyAuditMatter,
    KeyAuditMatters,
)


KEY_AUDIT_MATTER_HEADINGS = {
    "핵심감사사항",
    "핵심 감사사항",
    "핵심감사사항(Key Audit Matters)",
    "핵심감사사항 (Key Audit Matters)",
}
KAM_SECTION_END_HEADINGS = {
    "기타사항",
    "강조사항",
    "계속기업 관련 중요한 불확실성",
    "재무제표에 대한 경영진과 지배기구의 책임",
    "연결재무제표에 대한 경영진과 지배기구의 책임",
    "재무제표감사에 대한 감사인의 책임",
    "연결재무제표감사에 대한 감사인의 책임",
}
KAM_DETAIL_HEADINGS = {
    "핵심감사사항으로 결정된 이유",
    "핵심감사사항으로 결정한 이유",
    "핵심감사사항이 감사에서 다루어진 방법",
    "감사에서 다루어진 방법",
    "감사인의 대응",
    "감사절차",
}

def _normalize_heading(text: str) -> str:
    return "".join(text.split()).strip()


def _is_kam_heading(text: str) -> bool:
    normalized = _normalize_heading(text)

    return normalized.startswith("핵심감사사항")


def _is_kam_section_end_heading(
    text: str,
) -> bool:
    normalized = _normalize_heading(text)

    for heading in KAM_SECTION_END_HEADINGS:
        normalized_heading = _normalize_heading(
            heading
        )

        if normalized.startswith(
            normalized_heading
        ):
            return True

    return False


def _find_kam_heading_index(
    elements: list[Tag],
) -> int | None:
    for index, element in enumerate(elements):
        text = element.get_text(
            " ",
            strip=True,
        )

        if _is_kam_heading(text):
            return index

    return None

def _is_kam_detail_heading(
    text: str,
) -> bool:
    normalized = _normalize_heading(text)

    return any(
        normalized.startswith(
            _normalize_heading(heading)
        )
        for heading in KAM_DETAIL_HEADINGS
    )


def _is_kam_item_heading(
    element: Tag,
) -> bool:
    text = element.get_text(
        " ",
        strip=True,
    )

    if not text:
        return False

    if _is_kam_detail_heading(text):
        return False

    # 제목이 지나치게 길면 본문일 가능성이 큼
    if len(text) > 120:
        return False

    if _is_bold_element(element):
        return True

    # 번호형 제목 보조 지원
    if re.match(
        r"^\s*(?:\(\d+\)|\d+[.)]|[가-힣][.)])\s+",
        text,
    ):
        return True

    return False


def _collect_kam_section_elements(
    elements: list[Tag],
    heading_index: int,
) -> list[Tag]:
    section_elements: list[Tag] = []

    for element in elements[
        heading_index + 1:
    ]:
        text = element.get_text(
            " ",
            strip=True,
        )

        if not text:
            continue

        if _is_kam_section_end_heading(text):
            break

        section_elements.append(element)

    return section_elements


def _is_bold_element(
    element: Tag,
) -> bool:
    if element.name in {
        "b",
        "strong",
    }:
        return True

    if element.find(
        ["b", "strong"]
    ) is not None:
        return True

    for tag in element.find_all(True):
        usermark = str(
            tag.attrs.get(
                "USERMARK",
                tag.attrs.get(
                    "usermark",
                    "",
                ),
            )
        ).upper()

        if usermark == "B":
            return True

        style = str(
            tag.attrs.get(
                "style",
                "",
            )
        ).lower()

        if (
            "font-weight:bold" in style
            or "font-weight: bold" in style
            or "font-weight:700" in style
            or "font-weight: 700" in style
        ):
            return True

    return False


def _normalize_block_text(
    text: str,
) -> str:
    return re.sub(
        r"[ \t]+",
        " ",
        text,
    ).strip()


def _join_text_blocks(
    blocks: list[str],
) -> str:
    cleaned = [
        _normalize_block_text(block)
        for block in blocks
        if _normalize_block_text(block)
    ]

    return "\n\n".join(cleaned)


def _split_kam_items(
    elements: list[Tag],
) -> tuple[
    str | None,
    tuple[KeyAuditMatter, ...],
]:
    introduction_blocks: list[str] = []
    matters: list[KeyAuditMatter] = []

    current_title: str | None = None
    current_blocks: list[str] = []

    found_first_matter = False

    def flush_current_matter() -> None:
        nonlocal current_title
        nonlocal current_blocks

        text = _join_text_blocks(
            current_blocks
        )

        if text:
            matters.append(
                KeyAuditMatter(
                    title=current_title,
                    text=text,
                )
            )

        current_title = None
        current_blocks = []

    for element in elements:
        text = element.get_text(
            " ",
            strip=True,
        )

        if not text:
            continue

        if _is_kam_item_heading(element):
            if found_first_matter:
                flush_current_matter()

            current_title = text
            current_blocks = []
            found_first_matter = True
            continue

        if not found_first_matter:
            introduction_blocks.append(text)
            continue

        current_blocks.append(text)

    if found_first_matter:
        flush_current_matter()

    introduction_text = _join_text_blocks(
        introduction_blocks
    )

    return (
        introduction_text or None,
        tuple(matters),
    )


def _build_kam_result(
    heading: str,
    section_elements: list[Tag],
) -> KeyAuditMatters:
    introduction_text, matters = (
        _split_kam_items(
            section_elements
        )
    )

    if matters:
        return KeyAuditMatters(
            heading=heading,
            introduction_text=(
                introduction_text
            ),
            matters=matters,
        )

    full_text = _join_text_blocks(
        [
            element.get_text(
                " ",
                strip=True,
            )
            for element in section_elements
        ]
    )

    fallback_matters: tuple[
        KeyAuditMatter,
        ...,
    ] = ()

    if full_text:
        fallback_matters = (
            KeyAuditMatter(
                title=None,
                text=full_text,
            ),
        )

    return KeyAuditMatters(
        heading=heading,
        introduction_text=None,
        matters=fallback_matters,
    )


def _extract_document_blocks(
    soup: BeautifulSoup,
) -> list[Tag]:
    """
    감사보고서 본문을 문서 순서대로 탐색하기 위한
    대표 블록 요소를 추출한다.

    중첩된 태그가 중복 수집되지 않도록
    P, TD, DIV 중 최상위 블록만 반환한다.
    """
    blocks: list[Tag] = []

    for tag in soup.find_all(
        ["p", "td", "div"],
    ):
        text = tag.get_text(
            " ",
            strip=True,
        )

        if not text:
            continue

        parent = tag.find_parent(
            ["p", "td", "div"],
        )

        if parent is not None:
            parent_text = parent.get_text(
                " ",
                strip=True,
            )

            if parent_text == text:
                continue

        blocks.append(tag)

    return blocks


def parse_key_audit_matters(
    html: str,
) -> KeyAuditMatters | None:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    elements = _extract_document_blocks(
        soup
    )

    heading_index = _find_kam_heading_index(
        elements
    )

    if heading_index is None:
        return None

    heading_element = elements[
        heading_index
    ]

    heading = heading_element.get_text(
        " ",
        strip=True,
    )

    section_elements = (
        _collect_kam_section_elements(
            elements=elements,
            heading_index=heading_index,
        )
    )

    return _build_kam_result(
        heading=heading,
        section_elements=section_elements,
    )