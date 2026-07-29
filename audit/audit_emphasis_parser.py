from __future__ import annotations

import re

from bs4 import BeautifulSoup

from audit.models import AuditReportSection
from audit.parser_utils import (
    collect_section_body,
    extract_document_blocks,
    is_standalone_heading,
    split_inline_heading,
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


def parse_emphasis_of_matter(
    html: str,
) -> AuditReportSection | None:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )
    elements = extract_document_blocks(
        soup
    )

    for index, element in enumerate(
        elements
    ):
        text = element.get_text(
            " ",
            strip=True,
        )

        heading: str | None = None
        first_body: str | None = None

        if is_standalone_heading(
            text,
            EMPHASIS_HEADINGS,
        ):
            heading = text

        else:
            inline_result = (
                split_inline_heading(
                    text,
                    EMPHASIS_HEADINGS,
                    allow_whitespace_separator=True,
                )
            )

            if inline_result is not None:
                heading, first_body = (
                    inline_result
                )

        if heading is None:
            continue

        body = collect_section_body(
            elements=elements,
            heading_index=index,
            first_body=first_body,
            boundary_patterns=(
                SECTION_BOUNDARY_PATTERNS
            ),
            max_heading_length=120,
        )

        # 목차의 제목처럼 본문이 없는 후보는 건너뛴다.
        if not body:
            continue

        return AuditReportSection(
            heading=heading,
            text=body,
        )

    return None