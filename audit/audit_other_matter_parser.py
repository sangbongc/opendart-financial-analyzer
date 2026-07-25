from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from audit.models import AuditReportSection
from audit.parser_utils import (
    extract_document_blocks,
    join_text_blocks,
    normalize_heading,
    strip_number_prefix,
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
    re.compile(r"내부회계관리제도\s*감사\s*또는\s*검토"),
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

    # '기타사항(전기감사인 관련)'처럼 제목 뒤에 괄호 설명이 붙는 경우만 허용한다.
    return any(
        normalized.startswith(f"{heading}(")
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

    # 제목과 본문이 같은 블록에 있을 때는 구분 기호가 있는 경우만 인정한다.
    # 단순히 '기타사항 ...'으로 시작하는 일반 문장을 제목으로 오인하지 않는다.
    match = re.match(
        rf"^\s*(?:\d+[.)]|[가-힣][.)]|\([0-9가-힣]+\))?\s*"
        rf"(?P<heading>{heading_pattern})"
        rf"\s*[:：\-–—]\s*"
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

            # 블록 처음부터 다음 섹션 제목이면 즉시 경계로 인정한다.
            if not prefix:
                return match.start()

            # 같은 HTML 블록 안에 다음 섹션 제목이 붙은 경우를 처리한다.
            # DART 원문은 앞 문장 끝에 마침표가 없을 수 있으므로 문장부호를 요구하지 않는다.
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


def _is_other_section_heading(
    text: str,
) -> bool:
    cleaned = strip_number_prefix(text).strip()
    normalized = normalize_heading(cleaned)

    # 긴 일반 문장은 제목으로 보지 않는다.
    if len(normalized) > 120:
        return False

    for pattern in SECTION_BOUNDARY_PATTERNS:
        if pattern.fullmatch(cleaned):
            return True

    return False


def _collect_other_matter_body(
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

        # 다음 섹션 제목이 별도 블록으로 나온 경우 즉시 종료한다.
        if _is_other_section_heading(text):
            break

        # 다음 섹션 제목이 현재 블록 뒤쪽에 붙은 경우 제목 앞까지만 수집한다.
        current_text, boundary_found = (
            _split_before_next_section(text)
        )

        if current_text:
            body_blocks.append(current_text)

        if boundary_found:
            break

    return join_text_blocks(body_blocks)


def parse_other_matter(
    html: str,
) -> AuditReportSection | None:
    soup = BeautifulSoup(html, "html.parser")
    elements = extract_document_blocks(soup)

    for index, element in enumerate(elements):
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        heading: str | None = None
        first_body: str | None = None

        if _is_standalone_heading(
            text,
            OTHER_MATTER_HEADINGS,
        ):
            heading = text
        else:
            inline_result = _split_inline_heading(
                text,
                OTHER_MATTER_HEADINGS,
            )

            if inline_result is not None:
                heading, first_body = inline_result

        if heading is None:
            continue

        body = _collect_other_matter_body(
            elements=elements,
            heading_index=index,
            first_body=first_body,
        )

        # 목차의 '기타사항'이거나 실제 본문이 없는 경우 건너뛴다.
        # 이후에 실제 기타사항 단락이 있다면 반복문이 계속 찾아간다.
        if not body:
            continue

        return AuditReportSection(
            heading=heading,
            text=body,
        )

    return None