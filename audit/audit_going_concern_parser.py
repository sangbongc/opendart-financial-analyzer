from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from audit.models import AuditReportSection
from audit.parser_utils import (
    extract_document_blocks,
    join_text_blocks,
    normalize_heading,
    strip_number_prefix,
)


GOING_CONCERN_HEADINGS = {
    "계속기업 관련 중요한 불확실성",
    "계속기업과 관련된 중요한 불확실성",
    "계속기업과 관련한 중요한 불확실성",
    "계속기업 관련 중대한 불확실성",
    "계속기업과 관련된 중대한 불확실성",
    "계속기업과 관련한 중대한 불확실성",
    "계속기업 존속능력에 대한 중요한 불확실성",
    "계속기업 존속능력과 관련된 중요한 불확실성",
    "계속기업 존속능력에 관한 중요한 불확실성",
    "계속기업관련 중요한 불확실성",
    "계속기업 가정에 대한 중요한 불확실성",
    "계속기업 가정과 관련된 중요한 불확실성",
    "계속기업 가정과 관련한 중요한 불확실성",
    "계속기업 가정에 관한 중요한 불확실성",
    "계속기업 가정에 대한 중대한 불확실성",
}

# 계속기업 단락의 앞뒤에 나타날 수 있는 주요 감사보고서 섹션이다.
# 목차에서 제목을 잘못 잡았을 때에도 다음 목차 항목에서 즉시 끊을 수 있도록
# 감사의견, KAM, 강조사항, 기타사항, 책임 문단 등을 넓게 포함한다.


# 감사의견과 의견근거 안에서 언급되는 계속기업 문구는
# 독립된 계속기업 섹션으로 보지 않는다.
MODIFIED_OPINION_BASIS_HEADING_PATTERNS = (
    re.compile(r"^한정\s*의견\s*근거(?:\s|$)"),
    re.compile(r"^부적정\s*의견\s*근거(?:\s|$)"),
    re.compile(r"^의견\s*거절\s*근거(?:\s|$)"),
)

OPINION_SECTION_HEADING_PATTERNS = (
    re.compile(r"^감사\s*의견\s*근거(?:\s|$)"),
    *MODIFIED_OPINION_BASIS_HEADING_PATTERNS,
    re.compile(r"^(?:감사\s*)?의견(?:\s|$)"),
)

OPINION_SECTION_END_PATTERNS = (
    re.compile(r"^핵심\s*감사\s*사항(?:\s|$)"),
    re.compile(r"^강조\s*사항(?:\s|$)"),
    re.compile(r"^기타\s*사항(?:\s|$)"),
    re.compile(r"^(?:연결\s*)?재무제표에\s*대한\s*.*책임"),
    re.compile(r"^감사인의\s*책임(?:\s|$)"),
    re.compile(r"^내부회계관리제도"),
    re.compile(r"^감사\s*실시\s*내용(?:\s|$)"),
)

SECTION_BOUNDARY_PATTERNS = (
    re.compile(r"감사\s*의견"),
    re.compile(r"감사\s*의견\s*근거"),
    re.compile(r"한정\s*의견\s*근거"),
    re.compile(r"부적정\s*의견\s*근거"),
    re.compile(r"의견\s*거절\s*근거"),
    re.compile(r"핵심\s*감사\s*사항"),
    re.compile(r"강조\s*사항"),
    re.compile(r"기타\s*사항"),
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
        r"감사인의\s*(?:연결\s*)?"
        r"재무제표\s*감사에\s*대한\s*책임"
    ),
    re.compile(r"감사인의\s*책임"),
    re.compile(
        r"내부회계관리제도에\s*대한\s*"
        r"감사인의\s*감사보고서"
    ),
    re.compile(r"내부회계관리제도\s*감사\s*또는\s*검토"),
)




def _matches_section_start(
    text: str,
    patterns: tuple[re.Pattern[str], ...],
) -> bool:
    """블록 전체 또는 블록 맨 앞에 있는 섹션 제목을 판별한다."""
    cleaned = strip_number_prefix(text).strip()

    return any(
        pattern.match(cleaned) is not None
        for pattern in patterns
    )


def _is_opinion_section_heading(text: str) -> bool:
    return _matches_section_start(
        text,
        OPINION_SECTION_HEADING_PATTERNS,
    )


def _is_opinion_section_end_heading(text: str) -> bool:
    return _matches_section_start(
        text,
        OPINION_SECTION_END_PATTERNS,
    )

def _contains_going_concern_in_modified_opinion_basis(
    elements: list[Tag],
) -> bool:
    """
    한정의견·부적정의견·의견거절의 근거 영역에 계속기업 제목 문구가
    나오면 즉시 True를 반환한다.

    일반 감사의견은 검사 대상에서 제외한다. 일반 의견 문단은 뒤쪽의 실제
    계속기업 단락을 참조할 수 있기 때문이다.
    """
    inside_modified_basis = False
    normalized_headings = {
        normalize_heading(heading)
        for heading in GOING_CONCERN_HEADINGS
    }

    for element in elements:
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        cleaned = strip_number_prefix(text).strip()

        if any(
            pattern.match(cleaned) is not None
            for pattern in MODIFIED_OPINION_BASIS_HEADING_PATTERNS
        ):
            inside_modified_basis = True
            # 제목과 본문이 같은 블록에 붙은 경우도 검사해야 하므로
            # 여기서 continue하지 않는다.

        if inside_modified_basis and _is_opinion_section_end_heading(text):
            inside_modified_basis = False
            continue

        if not inside_modified_basis:
            continue

        normalized_text = normalize_heading(text)

        if any(
            heading in normalized_text
            for heading in normalized_headings
        ):
            return True

    return False


def _is_numbered_opinion_subheading(
    text: str,
    heading: str,
) -> bool:
    """
    의견근거 안의 ``(1) 계속기업 ...`` 같은 하위 항목인지 확인한다.
    """
    heading_start = text.find(heading)

    if heading_start < 0:
        return False

    prefix = text[:heading_start].rstrip()

    return bool(
        re.search(
            r"(?:\(\d+\)|\d+[.)]|[가-힣][.)])\s*$",
            prefix,
        )
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

    # 제목 뒤에 괄호로 부연 설명이 붙은 경우를 허용한다.
    return any(
        normalized.startswith(f"{heading}(")
        for heading in normalized_headings
    )


def _split_inline_heading(
    text: str,
    headings: set[str],
) -> tuple[str, str] | None:
    heading_pattern = "|".join(
        re.escape(heading).replace(
            r"\ ",
            r"\s*",
        )
        for heading in sorted(
            headings,
            key=len,
            reverse=True,
        )
    )

    match = re.match(
        rf"^\s*"
        rf"(?:"
        rf"\d+[.)]"
        rf"|[가-힣][.)]"
        rf"|\([0-9가-힣]+\)"
        rf")?"
        rf"\s*"
        rf"(?P<heading>{heading_pattern})"
        rf"(?:\s*[:：\-–—]\s*|\s+)"
        rf"(?P<body>.+)$",
        text,
        flags=re.DOTALL,
    )

    if match is None:
        return None

    heading = match.group(
        "heading"
    ).strip()

    body = match.group(
        "body"
    ).strip()

    if not body:
        return None

    return heading, body


def _split_embedded_heading(
    text: str,
    headings: set[str],
) -> tuple[str, str] | None:
    """
    하나의 HTML 블록 중간에 감사의견, 감사의견근거와 함께
    계속기업 제목과 본문이 합쳐진 경우를 분리한다.
    """
    heading_pattern = "|".join(
        re.escape(heading).replace(
            r"\ ",
            r"\s*",
        )
        for heading in sorted(
            headings,
            key=len,
            reverse=True,
        )
    )

    match = re.search(
        rf"(?P<heading>{heading_pattern})"
        rf"(?:\s*[:：\-–—]\s*|\s*)"
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

            # 블록 전체가 다음 섹션 제목이면 즉시 경계로 인정한다.
            if not prefix:
                return match.start()

            # DART 문서에서는 앞 문장과 다음 제목이 하나의 블록으로 합쳐지고
            # 앞 문장 끝에 마침표가 없는 경우도 있으므로 문장부호를 요구하지 않는다.
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

    # 긴 일반 문장은 섹션 제목으로 보지 않는다.
    if len(normalized) > 120:
        return False

    for pattern in SECTION_BOUNDARY_PATTERNS:
        if pattern.fullmatch(cleaned):
            return True

    return False


def _collect_going_concern_body(
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

        # 다음 섹션 제목이 독립된 HTML 블록인 경우 즉시 종료한다.
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



def _is_bold_tag(tag: Tag) -> bool:
    """DART HTML에서 굵게 표시된 인라인 섹션 제목인지 확인한다."""
    style = str(tag.get("style") or "").replace(" ", "").lower()

    return (
        tag.name in {"b", "strong"}
        or "font-weight:bold" in style
        or "font-weight:700" in style
    )


def _find_inline_dom_heading(
    soup: BeautifulSoup,
) -> tuple[str, str] | None:
    """
    하나의 P 블록 안에 감사의견·감사의견근거·계속기업 단락이
    연속해서 들어간 구형 DART HTML을 처리한다.

    코스나인처럼 계속기업 제목만 굵은 SPAN으로 표시된 경우,
    해당 SPAN 뒤의 같은 부모 블록 내용만 본문으로 추출한다.
    """
    normalized_headings = {
        normalize_heading(heading): heading
        for heading in GOING_CONCERN_HEADINGS
    }

    for tag in soup.find_all(["span", "b", "strong"]):
        if not _is_bold_tag(tag):
            continue

        own_text = tag.get_text(" ", strip=True)
        normalized = normalize_heading(
            strip_number_prefix(own_text)
        )

        canonical_heading = normalized_headings.get(normalized)

        if canonical_heading is None:
            continue

        parent = tag.parent

        if not isinstance(parent, Tag):
            continue

        body_parts: list[str] = []

        for sibling in tag.next_siblings:
            if isinstance(sibling, NavigableString):
                text = str(sibling).strip()

                if text:
                    body_parts.append(text)

                continue

            if not isinstance(sibling, Tag):
                continue

            sibling_text = sibling.get_text(" ", strip=True)

            if not sibling_text:
                continue

            # 같은 P 안에 다음 굵은 최상위 섹션 제목이 붙어 있으면 종료한다.
            if _is_bold_tag(sibling) and _is_other_section_heading(
                sibling_text
            ):
                break

            body_parts.append(sibling_text)

        body = join_text_blocks(body_parts)

        if body:
            return canonical_heading, body

    return None

def parse_going_concern_uncertainty(
    html: str,
) -> AuditReportSection | None:
    """
    적정의견 감사보고서의
    '계속기업 관련 중요한 불확실성' 단락을 추출한다.

    해당 단락이 없거나 목차에 제목만 존재하는 경우 None을 반환한다.
    """
    soup = BeautifulSoup(html, "html.parser")
    elements = extract_document_blocks(soup)

    # 가장 먼저 실행하는 강제 제외 필터다.
    # 수정의견 근거 안에 계속기업 제목 문구가 있으면
    # 독립된 계속기업 중요 불확실성 단락이 없는 것으로 처리한다.
    # 일반 감사의견에 포함된 단순 참조 문구는 차단하지 않는다.
    if _contains_going_concern_in_modified_opinion_basis(elements):
        return None

    # 구형 DART HTML은 감사의견, 감사의견근거, 계속기업 단락을
    # 하나의 P에 넣고 각 제목만 굵은 SPAN으로 구분하기도 한다.
    # 블록 텍스트가 "감사의견"으로 시작하므로 기존 블록 단위 검색으로는
    # 내부의 계속기업 제목을 절대 발견할 수 없다.
    dom_result = _find_inline_dom_heading(soup)

    if dom_result is not None:
        heading, body = dom_result

        return AuditReportSection(
            heading=heading,
            text=body,
        )

    inside_opinion_section = False

    for index, element in enumerate(elements):
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        if _is_opinion_section_heading(text):
            inside_opinion_section = True
            continue

        if _is_opinion_section_end_heading(text):
            inside_opinion_section = False

        heading: str | None = None
        first_body: str | None = None

        if _is_standalone_heading(
            text,
            GOING_CONCERN_HEADINGS,
        ):
            heading = text
        else:
            inline_result = _split_inline_heading(
                text,
                GOING_CONCERN_HEADINGS,
            )

            if inline_result is not None:
                heading, first_body = inline_result
            # 문서 블록 중간 어디서든 제목을 찾는 임베디드 탐색은 사용하지 않는다.
            # 이 방식은 의견근거 속 문구나 목차를 제목으로 오인한 뒤,
            # 감사실시내용 및 커뮤니케이션 표까지 본문으로 흘려보낼 수 있다.

        if heading is None:
            continue

        # 의견 또는 의견근거 단락 안에서 발견된 계속기업 문구는 무시한다.
        # 특히 ``(1) 계속기업 가정에 대한 중요한 불확실성``처럼
        # 수정의견 근거의 하위 항목으로 제시된 경우를 독립 섹션으로 보지 않는다.
        if inside_opinion_section:
            continue

        body = _collect_going_concern_body(
            elements=elements,
            heading_index=index,
            first_body=first_body,
        )

        # 목차의 제목이거나 실제 본문이 없는 후보는 건너뛴다.
        # 뒤쪽에 실제 단락이 있으면 반복문이 계속 탐색한다.
        if not body:
            continue

        return AuditReportSection(
            heading=heading,
            text=body,
        )

    return None