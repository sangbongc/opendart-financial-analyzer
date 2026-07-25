from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from audit.models import AuditReportSection
from audit.parser_utils import (
    normalize_heading,
    join_text_blocks,
    extract_document_blocks,
    strip_number_prefix,
)


EMPHASIS_HEADINGS = {
    "강조사항",
    "강조 사항",
}

SECTION_BOUNDARY_PATTERNS = (
    re.compile(r"핵심\s*감사\s*사항"),
    re.compile(r"기타\s*사항"),
    re.compile(
        r"계속기업\s*(?:과\s*)?관련(?:된)?\s*"
        r"중요한\s*불확실성"
    ),
    re.compile(
        r"(?:연결)?재무제표에\s*대한\s*"
        r"(?:회사\s*)?경영진과\s*지배기구의\s*책임"
    ),
    re.compile(
        r"(?:연결)?재무제표감사에\s*대한\s*"
        r"감사인의\s*책임"
    ),
    re.compile(
        r"감사인의\s*(?:연결)?재무제표감사에\s*대한\s*책임"
    ),
)





def _is_standalone_heading(
    text: str,
    headings: set[str],
) -> bool:
    normalized = normalize_heading(
        strip_number_prefix(text)
    )

    normalized_headings = {
        normalize_heading(heading)
        for heading in headings
    }

    if normalized in normalized_headings:
        return True

    return any(
        normalized.startswith(
            f"{heading}("
        )
        for heading in normalized_headings
    )


def _split_inline_heading(
    text: str,
    headings: set[str],
) -> tuple[str, str] | None:
    heading_pattern = "|".join(
        re.escape(heading).replace(r"\ ", r"\s*")
        for heading in sorted(
            headings,
            key=len,
            reverse=True,
        )
    )

    match = re.match(
        rf"^\s*(?:\d+[.)]|[가-힣][.)]|\([0-9가-힣]+\))?\s*"
        rf"(?P<heading>{heading_pattern})"
        rf"(?:\s*[:：\-–—]\s*|\s+)"
        rf"(?P<body>.+)$",
        text,
        flags=re.DOTALL,
    )

    if match is None:
        return None

    heading = match.group("heading").strip()
    body = match.group("body").strip()

    if not body:
        return None

    return heading, body


def _find_embedded_boundary_start(
    text: str,
) -> int | None:
    earliest_start: int | None = None

    for pattern in SECTION_BOUNDARY_PATTERNS:
        for match in pattern.finditer(text):
            prefix = text[:match.start()].rstrip()

            # 별도 블록의 제목이거나, 앞 문장이 끝난 직후 붙은 제목만 경계로 본다.
            if prefix and not prefix.endswith((".", "!", "?", ":", "：")):
                continue

            if (
                earliest_start is None
                or match.start() < earliest_start
            ):
                earliest_start = match.start()

            break

    return earliest_start


def _split_before_next_section(
    text: str,
) -> tuple[str, bool]:
    boundary_start = _find_embedded_boundary_start(text)

    if boundary_start is None:
        return text.strip(), False

    return text[:boundary_start].strip(), True


def _is_other_section_heading(text: str) -> bool:
    cleaned = strip_number_prefix(text)

    if len(normalize_heading(cleaned)) > 100:
        return False

    for pattern in SECTION_BOUNDARY_PATTERNS:
        if pattern.fullmatch(cleaned):
            return True

    return False


def _collect_emphasis_body(
    elements: list[Tag],
    heading_index: int,
    first_body: str | None,
) -> str:
    body_blocks: list[str] = []

    if first_body:
        first_text, boundary_found = (
            _split_before_next_section(first_body)
        )

        if first_text:
            body_blocks.append(first_text)

        if boundary_found:
            return join_text_blocks(body_blocks)

    for element in elements[heading_index + 1:]:
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        if _is_other_section_heading(text):
            break

        current_text, boundary_found = (
            _split_before_next_section(text)
        )

        if current_text:
            body_blocks.append(current_text)

        if boundary_found:
            break

    return join_text_blocks(body_blocks)


def parse_emphasis_of_matter(
    html: str,
) -> AuditReportSection | None:
    soup = BeautifulSoup(html, "html.parser")
    elements = extract_document_blocks(soup)

    for index, element in enumerate(elements):
        text = element.get_text(" ", strip=True)

        heading: str | None = None
        first_body: str | None = None

        if _is_standalone_heading(
            text,
            EMPHASIS_HEADINGS,
        ):
            heading = text
        else:
            inline_result = _split_inline_heading(
                text,
                EMPHASIS_HEADINGS,
            )

            if inline_result is not None:
                heading, first_body = inline_result

        if heading is None:
            continue

        body = _collect_emphasis_body(
            elements=elements,
            heading_index=index,
            first_body=first_body,
        )

        # 목차의 제목처럼 본문이 없는 후보는 건너뛴다.
        if not body:
            continue

        return AuditReportSection(
            heading=heading,
            text=body,
        )

    return None