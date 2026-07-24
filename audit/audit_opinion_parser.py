from dataclasses import dataclass
import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


OPINION_TYPE_BY_HEADING = {
    "감사의견": "적정의견",
    "한정의견": "한정의견",
    "부적정의견": "부적정의견",
    "의견거절": "의견거절",
}


BASIS_HEADING_BY_OPINION_HEADING = {
    "감사의견": "감사의견근거",
    "한정의견": "한정의견근거",
    "부적정의견": "부적정의견근거",
    "의견거절": "의견거절근거",
}


MODIFIED_OPINION_HEADINGS = {
    "한정의견",
    "부적정의견",
    "의견거절",
}


HEADING_ALIASES = {
    "감사의견의 근거": "감사의견근거",
    "한정의견의 근거": "한정의견근거",
    "부적정의견의 근거": "부적정의견근거",
    "의견거절의 근거": "의견거절근거",
}


SECTION_HEADINGS = {
    *OPINION_TYPE_BY_HEADING,
    *BASIS_HEADING_BY_OPINION_HEADING.values(),
    *HEADING_ALIASES,
    "계속기업 관련 중요한 불확실성",
    "핵심감사사항",
    "강조사항",
    "기타사항",
    "재무제표에 대한 경영진과 지배기구의 책임",
    "경영진과 지배기구의 책임",
    "경영진의 책임",
    "재무제표감사에 대한 감사인의 책임",
    "재무제표에 대한 감사인의 책임",
    "감사인의 책임",
}


OPINION_BODY_KEYWORDS = (
    "재무제표를 감사하였습니다",
    "연결재무제표를 감사하였습니다",
    "우리의 의견으로는",
    "중요성의 관점에서",
    "재무상태",
    "재무성과",
    "현금흐름",
)


OPINION_TYPE_KEYWORDS = {
    "감사의견": (
        "우리의 의견으로는",
        "공정하게 표시하고 있습니다",
    ),
    "한정의견": (
        "한정의견근거",
        "영향을 제외하고는",
        "가능한 영향을 제외하고는",
    ),
    "부적정의견": (
        "부적정의견근거",
        "공정하게 표시하고 있지 않습니다",
    ),
    "의견거절": (
        "의견거절근거",
        "감사의견을 표명하지 않습니다",
        "의견을 표명하지 않습니다",
        "감사의견을 표명할 수 없습니다",
        "의견을 표명할 수 없습니다",
        "충분하고 적합한 감사증거를 입수할 수 없었습니다",
        "충분하고 적합한 감사증거를 입수하지 못하였습니다",
    ),
}


XML_CONTENT_TAG_NAMES = {
    "p",
    "tu",
    "te",
}

HTML_CONTENT_TAG_NAMES = {
    "p",
    "div",
    "td",
    "th",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}

IGNORED_PARENT_TAG_NAMES = {
    "script",
    "style",
    "noscript",
}


REASON_HEADING_PATTERNS = (
    re.compile(
        r"^\s*\d+\s*[.)]\s*(?P<title>.+?)\s*$"
    ),
    re.compile(
        r"^\s*\(\s*\d+\s*\)\s*(?P<title>.+?)\s*$"
    ),
    re.compile(
        r"^\s*[가-하]\s*[.)]\s*(?P<title>.+?)\s*$"
    ),
)

NUMBERED_REASON_PATTERN = re.compile(
    r"(?<!\S)(\(\s*\d+\s*\)|\d+\s*[.)])\s*"
)



@dataclass(frozen=True)
class AuditOpinion:
    """
    재무제표 감사의견 파싱 결과.
    """

    opinion_type: str
    heading: str
    opinion_text: str
    basis_heading: str | None
    opinion_basis_text: str | None
    basis_reasons: tuple[str, ...]


@dataclass(frozen=True)
class _TextUnit:
    """
    문서 순서를 유지한 최소 텍스트 단위.

    block_id가 같으면 같은 P, TU, TE 안의 텍스트이고,
    heading은 해당 단위가 실제 섹션 제목일 때만 설정된다.
    """

    text: str
    block_id: int
    heading: str | None


@dataclass(frozen=True)
class _SectionCandidate:
    heading: str
    unit_index: int
    section_text: str
    score: int




def _normalize_text(text: str) -> str:
    """
    줄바꿈과 연속된 공백을 하나의 공백으로 정리한다.
    """
    return " ".join(text.split())


def _has_bold_ancestor(
    text_node: NavigableString,
    content_parent: Tag,
) -> bool:
    """
    텍스트 노드부터 본문 블록까지 올라가며
    USERMARK="B"가 지정된 태그가 있는지 확인한다.
    """
    parent = text_node.parent

    while isinstance(parent, Tag):
        usermark = (
            parent.get("USERMARK")
            or parent.get("usermark")
        )

        if str(usermark).upper() == "B":
            return True

        if parent.name.lower() in {"b", "strong"}:
            return True

        style = str(parent.get("style", "")).lower()

        if (
            "font-weight:bold" in style.replace(" ", "")
            or "font-weight:700" in style.replace(" ", "")
        ):
            return True

        if parent is content_parent:
            break

        parent = parent.parent

    return False


def _find_content_parent(
    text_node: NavigableString,
) -> Tag | None:
    """
    텍스트 노드가 속한 가장 가까운 P, TU, TE를 찾는다.
    """
    parent = text_node.parent

    while isinstance(parent, Tag):
        tag_name = parent.name.lower()

        if tag_name in IGNORED_PARENT_TAG_NAMES:
            return None

        if (
            tag_name in XML_CONTENT_TAG_NAMES
            or tag_name in HTML_CONTENT_TAG_NAMES
        ):
            return parent

        parent = parent.parent

    return None


def _detect_exact_heading(
    text: str,
    is_bold: bool,
) -> str | None:
    """
    실제 섹션 제목인지 판별한다.

    본문 문장에 포함된 '한정의견근거 단락' 같은 표현을
    제목으로 오인하지 않도록 정확히 일치하는 텍스트만 본다.
    굵은 텍스트를 우선 사용하되, 제목이 굵지 않은 보고서도
    처리할 수 있도록 정확히 일치하면 보완적으로 허용한다.
    """
    normalized = _normalize_text(text)

    if normalized not in SECTION_HEADINGS:
        return None

    canonical_heading = HEADING_ALIASES.get(
        normalized,
        normalized,
    )

    if is_bold:
        return canonical_heading

    return canonical_heading


def _collect_text_units(
    soup: BeautifulSoup,
) -> list[_TextUnit]:
    """
    문서의 텍스트 노드를 순서대로 수집한다.

    개별 텍스트 노드뿐 아니라 같은 P, TU, TE 안의 텍스트를
    모두 합친 값도 제목 후보로 판정한다. 따라서 제목이
    여러 SPAN으로 분리된 경우도 인식한다.
    """
    raw_units: list[
        tuple[str, int, bool, Tag]
    ] = []

    block_ids: dict[int, int] = {}
    block_parents: dict[int, Tag] = {}
    next_block_id = 0

    for node in soup.descendants:
        if not isinstance(node, NavigableString):
            continue

        text = _normalize_text(str(node))

        if not text:
            continue

        content_parent = _find_content_parent(node)

        if content_parent is None:
            continue

        parent_key = id(content_parent)

        if parent_key not in block_ids:
            block_ids[parent_key] = next_block_id
            block_parents[next_block_id] = content_parent
            next_block_id += 1

        block_id = block_ids[parent_key]

        is_bold = _has_bold_ancestor(
            text_node=node,
            content_parent=content_parent,
        )

        raw_units.append(
            (
                text,
                block_id,
                is_bold,
                content_parent,
            )
        )

    block_text_parts: dict[int, list[str]] = {}
    block_has_bold: dict[int, bool] = {}

    for text, block_id, is_bold, _ in raw_units:
        block_text_parts.setdefault(
            block_id,
            [],
        ).append(text)

        block_has_bold[block_id] = (
            block_has_bold.get(block_id, False)
            or is_bold
        )

    block_headings: dict[int, str] = {}

    for block_id, parts in block_text_parts.items():
        block_text = _normalize_text(
            " ".join(parts)
        )

        heading = _detect_exact_heading(
            text=block_text,
            is_bold=block_has_bold.get(
                block_id,
                False,
            ),
        )

        if heading is not None:
            block_headings[block_id] = heading

    units: list[_TextUnit] = []
    heading_emitted: set[int] = set()

    for text, block_id, is_bold, _ in raw_units:
        heading = _detect_exact_heading(
            text=text,
            is_bold=is_bold,
        )

        block_heading = block_headings.get(block_id)

        if (
            heading is None
            and block_heading is not None
            and block_id not in heading_emitted
        ):
            heading = block_heading

        if heading is not None:
            heading_emitted.add(block_id)

        units.append(
            _TextUnit(
                text=text,
                block_id=block_id,
                heading=heading,
            )
        )

    return units


def _join_units(
    units: list[_TextUnit],
) -> str:
    """
    같은 문단 내부 텍스트는 공백으로, 서로 다른 문단은
    빈 줄로 연결한다.
    """
    if not units:
        return ""

    paragraphs: list[str] = []
    current_block_id = units[0].block_id
    current_parts: list[str] = []

    for unit in units:
        if unit.block_id != current_block_id:
            paragraph = _normalize_text(
                " ".join(current_parts)
            )

            if paragraph:
                paragraphs.append(paragraph)

            current_block_id = unit.block_id
            current_parts = []

        current_parts.append(unit.text)

    paragraph = _normalize_text(
        " ".join(current_parts)
    )

    if paragraph:
        paragraphs.append(paragraph)

    return "\n\n".join(paragraphs)


def _extract_section_text(
    units: list[_TextUnit],
    heading_index: int,
) -> str:
    """
    제목 다음 텍스트부터 다음 섹션 제목 직전까지 추출한다.
    """
    section_units: list[_TextUnit] = []

    for unit in units[heading_index + 1:]:
        if unit.heading is not None:
            break

        section_units.append(unit)

    return _join_units(section_units)


def _score_opinion_text(
    heading: str,
    text: str,
    has_basis: bool,
) -> int:
    """
    목차나 사업보고서 표가 아니라 실제 감사의견 본문일
    가능성을 평가한다.

    대응하는 의견근거 단락과 의견 유형별 고유 문구가 있으면
    높은 점수를 부여하고, 표 형태의 장문 후보는 감점한다.
    """
    score = 0

    score += 2 * sum(
        keyword in text
        for keyword in OPINION_BODY_KEYWORDS
    )

    score += 6 * sum(
        keyword in text
        for keyword in OPINION_TYPE_KEYWORDS.get(
            heading,
            (),
        )
    )

    if has_basis:
        score += 20

    if len(text) < 30:
        score -= 10

    if len(text) > 8_000:
        score -= 15

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if lines:
        table_like_lines = sum(
            line == "-"
            or line.isdigit()
            or len(line) <= 3
            for line in lines
        )

        if table_like_lines / len(lines) >= 0.35:
            score -= 15

    return score


def _has_expected_basis_after(
    units: list[_TextUnit],
    heading: str,
    heading_index: int,
) -> bool:
    """
    현재 의견 후보 뒤에 대응하는 의견근거 제목이 존재하는지
    확인한다. 다음 감사의견 후보를 만나면 탐색을 중단한다.
    """
    expected_heading = (
        BASIS_HEADING_BY_OPINION_HEADING[heading]
    )

    for unit in units[heading_index + 1:]:
        if unit.heading == expected_heading:
            return True

        if unit.heading in OPINION_TYPE_BY_HEADING:
            return False

    return False


def _find_best_opinion_candidate(
    units: list[_TextUnit],
) -> _SectionCandidate | None:
    """
    의견 제목 후보 중 실제 본문 가능성이 가장 높은 것을 고른다.
    """
    candidates: list[_SectionCandidate] = []

    for index, unit in enumerate(units):
        if unit.heading not in OPINION_TYPE_BY_HEADING:
            continue

        section_text = _extract_section_text(
            units=units,
            heading_index=index,
        )

        has_basis = _has_expected_basis_after(
            units=units,
            heading=unit.heading,
            heading_index=index,
        )

        candidates.append(
            _SectionCandidate(
                heading=unit.heading,
                unit_index=index,
                section_text=section_text,
                score=_score_opinion_text(
                    heading=unit.heading,
                    text=section_text,
                    has_basis=has_basis,
                ),
            )
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda candidate: (
            candidate.score,
            -abs(len(candidate.section_text) - 1_500),
        ),
    )


def _find_basis_candidate(
    units: list[_TextUnit],
    opinion_candidate: _SectionCandidate,
) -> _SectionCandidate | None:
    """
    선택된 의견 단락 뒤에서 대응하는 의견근거를 찾는다.
    """
    expected_heading = (
        BASIS_HEADING_BY_OPINION_HEADING[
            opinion_candidate.heading
        ]
    )

    for index in range(
        opinion_candidate.unit_index + 1,
        len(units),
    ):
        unit = units[index]

        if unit.heading != expected_heading:
            continue

        section_text = _extract_section_text(
            units=units,
            heading_index=index,
        )

        return _SectionCandidate(
            heading=expected_heading,
            unit_index=index,
            section_text=section_text,
            score=0,
        )

    return None


def _looks_like_full_audit_report(
    soup: BeautifulSoup,
) -> bool:
    """
    사업보고서 요약표가 아니라 감사보고서 전문인지 확인한다.
    """
    document_text = " ".join(soup.stripped_strings)

    responsibility_markers = (
        "재무제표감사에 대한 감사인의 책임",
        "재무제표에 대한 감사인의 책임",
        "감사인의 책임",
        "재무제표에 대한 경영진과 지배기구의 책임",
        "경영진과 지배기구의 책임",
        "경영진의 책임",
    )

    return any(
        marker in document_text
        for marker in responsibility_markers
    )


def _build_soup(document_text: str) -> BeautifulSoup:
    """
    원본 DART XML과 Playwright로 렌더링한 HTML을 모두 읽는다.
    """
    lowered = document_text[:2_000].lower()

    looks_like_dart_xml = (
        "<document-name" in lowered
        or "<?xml" in lowered
        or "<tu" in lowered
        or "<te" in lowered
    )

    parser = "xml" if looks_like_dart_xml else "html.parser"

    return BeautifulSoup(document_text, parser)


def _split_paragraphs(
    text: str,
) -> list[str]:
    """
    의견근거 본문을 비어 있지 않은 문단 단위로 나눈다.
    """
    return [
        _normalize_text(paragraph)
        for paragraph in re.split(
            r"\n\s*\n",
            text,
        )
        if _normalize_text(paragraph)
    ]


def _extract_reason_heading(
    paragraph: str,
) -> str | None:
    """
    번호 또는 항목 기호가 붙은 사유 제목을 추출한다.
    """
    normalized = _normalize_text(paragraph)

    for pattern in REASON_HEADING_PATTERNS:
        match = pattern.match(normalized)

        if match is None:
            continue

        title = _normalize_text(
            match.group("title")
        )

        if title:
            return title

    return None

def _extract_basis_reasons(
    opinion_heading: str,
    basis_text: str | None,
) -> tuple[str, ...]:
    """
    수정의견의 근거 본문을 개별 사유 단위로 분리한다.
    """
    if (
        opinion_heading
        not in MODIFIED_OPINION_HEADINGS
    ):
        return ()

    if not basis_text:
        return ()

    reasons: list[str] = []

    for block in _split_numbered_reason_blocks(
        basis_text
    ):
        reason = _remove_reason_number(block)

        if reason:
            reasons.append(reason)

    return tuple(reasons)


def _split_numbered_reason_blocks(
    text: str,
) -> list[str]:
    """
    의견근거 본문에서 번호형 사유 시작 지점을 기준으로
    개별 사유 블록을 분리한다.

    번호가 문단 중간에 붙어 있어도 인식한다.
    """
    normalized = text.strip()

    if not normalized:
        return []

    matches = list(
        NUMBERED_REASON_PATTERN.finditer(
            normalized
        )
    )

    if not matches:
        return [normalized]

    blocks: list[str] = []

    # 첫 번호 앞에 유효한 본문이 있는 경우 보존
    prefix = normalized[:matches[0].start()].strip()

    if prefix:
        blocks.append(prefix)

    for index, match in enumerate(matches):
        start = match.start()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(normalized)
        )

        block = normalized[start:end].strip()

        if block:
            blocks.append(block)

    return blocks


def _remove_reason_number(
    text: str,
) -> str:
    """
    사유 블록 앞의 번호 표시를 제거한다.
    """
    return NUMBERED_REASON_PATTERN.sub(
        "",
        text,
        count=1,
    ).strip()



def parse_audit_opinion(
    document_text: str,
) -> AuditOpinion:
    """
    감사보고서 XML 또는 렌더링 HTML에서 감사의견과
    감사의견 근거를 추출한다.

    상위 문단 배치가 아니라 실제 텍스트 노드와 섹션 제목의
    문서 순서를 기준으로 본문 경계를 판별한다.
    """
    if not document_text.strip():
        raise ValueError(
            "감사보고서 내용이 비어 있습니다."
        )

    soup = _build_soup(document_text)

    if not _looks_like_full_audit_report(soup):
        raise ValueError(
            "입력 문서가 감사보고서 전문으로 보이지 "
            "않습니다. 사업보고서의 감사의견 요약은 "
            "business_report_audit_parser를 사용하세요."
        )

    units = _collect_text_units(soup)

    opinion_candidate = (
        _find_best_opinion_candidate(units)
    )

    if opinion_candidate is None:
        raise ValueError(
            "감사의견 단락 제목을 찾을 수 없습니다."
        )

    if not opinion_candidate.section_text:
        raise ValueError(
            "감사의견 단락의 본문을 찾을 수 없습니다."
        )

    basis_candidate = _find_basis_candidate(
        units=units,
        opinion_candidate=opinion_candidate,
    )

    if basis_candidate is None:
        basis_heading = None
        opinion_basis_text = None
    else:
        basis_heading = basis_candidate.heading
        opinion_basis_text = (
            basis_candidate.section_text
            or None
        )
    basis_reasons = _extract_basis_reasons(
    opinion_heading=opinion_candidate.heading,
    basis_text=opinion_basis_text,
)
    return AuditOpinion(
        opinion_type=OPINION_TYPE_BY_HEADING[
            opinion_candidate.heading
        ],
        heading=opinion_candidate.heading,
        opinion_text=opinion_candidate.section_text,
        basis_heading=basis_heading,
        opinion_basis_text=opinion_basis_text,
        basis_reasons=basis_reasons,
    )