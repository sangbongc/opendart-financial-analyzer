from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import Tag


OPINION_TYPE_BY_HEADING = {
    "감사의견": "적정의견",
    "한정의견": "한정의견",
    "부적정의견": "부적정의견",
    "의견거절": "의견거절",
}


@dataclass(frozen=True)
class AuditOpinion:
    """
    재무제표 감사의견 파싱 결과.
    """

    opinion_type: str
    heading: str
    opinion_text: str


def _normalize_text(
    text: str,
) -> str:
    """
    줄바꿈과 연속된 공백을 하나의 공백으로 정리한다.
    """
    return " ".join(text.split())


def _get_tag_text(
    tag: Tag,
) -> str:
    """
    태그 내부의 텍스트를 정규화하여 반환한다.
    """
    return _normalize_text(
        tag.get_text(
            " ",
            strip=True,
        )
    )


def _is_bold_tag(
    tag: Tag,
) -> bool:
    """
    태그 또는 하위 태그에 USERMARK="B"가 있는지 확인한다.

    다음 두 구조를 모두 처리한다.

    <P USERMARK="B">감사의견</P>

    <P>
        <SPAN USERMARK="B">감사의견근거</SPAN>
    </P>
    """
    if tag.get("USERMARK") == "B":
        return True

    return tag.find(
        attrs={
            "USERMARK": "B",
        }
    ) is not None


def _find_opinion_heading(
    soup: BeautifulSoup,
) -> Tag:
    """
    재무제표 감사의견 단락의 제목 태그를 찾는다.

    단락 제목에 따라 의견 유형을 판단하므로
    정확히 다음 제목만 검색한다.

    - 감사의견
    - 한정의견
    - 부적정의견
    - 의견거절
    """
    for tag in soup.find_all("P"):
        heading = _get_tag_text(tag)

        if heading not in OPINION_TYPE_BY_HEADING:
            continue

        if not _is_bold_tag(tag):
            continue

        return tag

    expected_headings = ", ".join(
        OPINION_TYPE_BY_HEADING,
    )

    raise ValueError(
        "감사의견 단락 제목을 찾을 수 없습니다. "
        f"예상 제목: {expected_headings}"
    )


def _extract_opinion_text(
    heading_tag: Tag,
) -> str:
    """
    의견 제목 다음부터 다음 굵은 제목 전까지의
    문단을 감사의견 본문으로 추출한다.
    """
    paragraphs: list[str] = []

    current = heading_tag.find_next_sibling()

    while current is not None:
        if not isinstance(current, Tag):
            current = current.find_next_sibling()
            continue

        text = _get_tag_text(current)

        if not text:
            current = current.find_next_sibling()
            continue

        # 감사의견근거와 같은 다음 단락 제목을 만나면 종료한다.
        if _is_bold_tag(current):
            break

        paragraphs.append(text)

        current = current.find_next_sibling()

    if not paragraphs:
        raise ValueError(
            "감사의견 단락의 본문을 찾을 수 없습니다."
        )

    return "\n\n".join(paragraphs)


def parse_audit_opinion(
    xml_text: str,
) -> AuditOpinion:
    """
    감사보고서 XML에서 재무제표 감사의견을 추출한다.

    의견 유형은 감사보고서의 의견 단락 제목으로 판단한다.

    - 감사의견   -> 적정의견
    - 한정의견   -> 한정의견
    - 부적정의견 -> 부적정의견
    - 의견거절   -> 의견거절
    """
    if not xml_text.strip():
        raise ValueError(
            "감사보고서 XML 내용이 비어 있습니다."
        )

    soup = BeautifulSoup(
        xml_text,
        "xml",
    )

    heading_tag = _find_opinion_heading(
        soup,
    )

    heading = _get_tag_text(
        heading_tag,
    )

    opinion_type = OPINION_TYPE_BY_HEADING[
        heading
    ]

    opinion_text = _extract_opinion_text(
        heading_tag,
    )

    return AuditOpinion(
        opinion_type=opinion_type,
        heading=heading,
        opinion_text=opinion_text,
    )