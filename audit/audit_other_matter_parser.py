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


OTHER_MATTER_HEADINGS = {
    "기타사항",
    "기타 사항",
}

# 기타사항 다음에 나올 수 있는 감사보고서의 주요 섹션 제목이다.
# 목차의 '기타사항'을 잘못 잡은 경우에도 다음 목차 항목에서 즉시 끊도록
# 감사의견·책임 문단 등 앞뒤 섹션을 넓게 포함한다.
SECTION_BOUNDARY_PATTERNS = (
    re.compile(r"감사\s*의견"),
    re.compile(r"감사\s*의견\s*근거"),
    re.compile(r"한정\s*의견\s*근거"),
    re.compile(r"부적정\s*의견\s*근거"),
    re.compile(r"의견\s*거절\s*근거"),
    re.compile(r"핵심\s*감사\s*사항"),
    re.compile(r"강조\s*사항"),
    re.compile(
        r"계속기업\s*(?:과\s*)?관련(?:된)?\s*"
        r"중요한\s*불확실성"
    ),
    re.compile(
        r"(?:연결\s*)?재무제표에\s*대한\s*"
        r"(?:(?:회사|경영진)(?:의)?\s*)?"
        r"경영진과\s*지배기구의\s*책임"
    ),
    re.compile(
        r"(?:연결\s*)?재무제표에\s*대한\s*"
        r"(?:회사(?:의)?\s*)?경영진의\s*책임"
    ),
    re.compile(
        r"(?:연결\s*)?재무제표에\s*대한\s*"
        r"지배기구의\s*책임"
    ),
    re.compile(
        r"(?:연결\s*)?재무제표\s*감사에\s*대한\s*"
        r"감사인의\s*책임"
    ),
    re.compile(
        r"감사인의\s*(?:연결\s*)?재무제표\s*감사에\s*대한\s*책임"
    ),
    re.compile(r"감사인의\s*책임"),
    re.compile(
        r"내부회계관리제도에\s*대한\s*"
        r"감사인의\s*감사보고서"
    ),
    re.compile(
        r"내부회계관리제도\s*감사\s*또는\s*검토"
    ),
    re.compile(
    r"(?:연결\s*)?내부회계관리제도에\s*대한\s*"
    r"경영진과\s*지배기구의\s*책임"
    ),
    re.compile(
    r"(?:연결\s*)?내부회계관리제도\s*감사에\s*대한\s*"
    r"감사인의\s*책임"
    ),
)


def parse_other_matter(
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

        if not text:
            continue

        heading: str | None = None
        first_body: str | None = None

        if is_standalone_heading(
            text,
            OTHER_MATTER_HEADINGS,
        ):
            heading = text

        else:
            inline_result = (
                split_inline_heading(
                    text,
                    OTHER_MATTER_HEADINGS,
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

        # 목차의 '기타사항'이거나 실제 본문이 없는 경우 건너뛴다.
        if not body:
            continue

        return AuditReportSection(
            heading=heading,
            text=body,
        )

    return None