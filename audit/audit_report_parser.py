from dataclasses import dataclass
from enum import Enum

from bs4 import BeautifulSoup, Tag


class AuditReportDocumentType(Enum):
    AUDIT_REPORT = "audit_report"
    BUSINESS_REPORT = "business_report"
    UNKNOWN = "unknown"


AUDIT_REPORT_DOCUMENT_NAMES = {
    "감사보고서",
    "연결감사보고서",
}

BUSINESS_REPORT_DOCUMENT_NAMES = {
    "사업보고서",
    "반기보고서",
    "분기보고서",
}

AUDIT_SECTION_HEADINGS = {
    "회계감사인의 감사의견 등",
    "회계감사인의 감사의견",
    "감사인의 감사의견 등",
    "감사인의 감사의견",
    "감사인의 감사 의견",
}

FULL_AUDIT_REPORT_MARKERS = (
    "재무제표감사에 대한 감사인의 책임",
    "재무제표에 대한 감사인의 책임",
    "감사인의 책임",
    "재무제표에 대한 경영진과 지배기구의 책임",
    "경영진과 지배기구의 책임",
    "경영진의 책임",
)

OPINION_MARKERS = (
    "감사의견",
    "한정의견",
    "부적정의견",
    "의견거절",
)


@dataclass(frozen=True)
class AuditReportDocument:
    document_code: str
    document_name: str
    document_type: AuditReportDocumentType
    company_name: str
    company_code: str | None
    xml_text: str


def _normalize_text(text: str) -> str:
    return "".join(text.split())


def _matches_document_name(
    document_name: str,
    candidates: set[str],
) -> bool:
    normalized_name = _normalize_text(document_name)

    return any(
        _normalize_text(candidate) == normalized_name
        for candidate in candidates
    )


def _detect_document_type(
    document_name: str,
) -> AuditReportDocumentType:
    if _matches_document_name(
        document_name,
        AUDIT_REPORT_DOCUMENT_NAMES,
    ):
        return AuditReportDocumentType.AUDIT_REPORT

    if _matches_document_name(
        document_name,
        BUSINESS_REPORT_DOCUMENT_NAMES,
    ):
        return AuditReportDocumentType.BUSINESS_REPORT

    return AuditReportDocumentType.UNKNOWN


def _has_audit_section(
    soup: BeautifulSoup,
) -> bool:
    for title in soup.find_all(
        lambda tag: (
            isinstance(tag, Tag)
            and tag.name.lower() == "title"
        )
    ):
        normalized_text = _normalize_text(
            title.get_text(" ", strip=True)
        )

        if any(
            _normalize_text(heading)
            in normalized_text
            for heading in AUDIT_SECTION_HEADINGS
        ):
            return True

    has_opinion_field = soup.find(
        lambda tag: (
            isinstance(tag, Tag)
            and (
                str(
                    tag.get("ACODE")
                    or tag.get("acode")
                    or ""
                ).startswith("OPN_")
                or str(
                    tag.get("AUNIT")
                    or tag.get("aunit")
                    or ""
                ).startswith("OPN_")
            )
        )
    )

    return has_opinion_field is not None


def _looks_like_full_audit_report(
    soup: BeautifulSoup,
) -> bool:
    document_text = " ".join(
        soup.stripped_strings
    )

    has_responsibility_section = any(
        marker in document_text
        for marker in FULL_AUDIT_REPORT_MARKERS
    )
    has_opinion_section = any(
        marker in document_text
        for marker in OPINION_MARKERS
    )

    return (
        has_responsibility_section
        and has_opinion_section
    )


def _find_tag_case_insensitive(
    soup: BeautifulSoup,
    tag_name: str,
) -> Tag | None:
    return soup.find(
        lambda tag: (
            isinstance(tag, Tag)
            and tag.name.lower() == tag_name.lower()
        )
    )


def parse_audit_report_document(
    xml_text: str,
) -> AuditReportDocument:
    """
    원본 DART XML의 문서 메타데이터와 문서 유형을 판별한다.
    """
    if not xml_text.strip():
        raise ValueError(
            "공시 XML 내용이 비어 있습니다."
        )

    soup = BeautifulSoup(
        xml_text,
        "xml",
    )

    document_name_tag = _find_tag_case_insensitive(
        soup,
        "DOCUMENT-NAME",
    )
    company_name_tag = _find_tag_case_insensitive(
        soup,
        "COMPANY-NAME",
    )

    if document_name_tag is None:
        raise ValueError(
            "DOCUMENT-NAME 태그를 찾을 수 없습니다."
        )

    if company_name_tag is None:
        raise ValueError(
            "COMPANY-NAME 태그를 찾을 수 없습니다."
        )

    document_code = (
        document_name_tag.get("ACODE")
        or document_name_tag.get("acode")
    )

    if not document_code:
        raise ValueError(
            "DOCUMENT-NAME의 ACODE를 찾을 수 없습니다."
        )

    document_name = document_name_tag.get_text(
        " ",
        strip=True,
    )
    company_name = company_name_tag.get_text(
        " ",
        strip=True,
    )
    company_code = (
        company_name_tag.get("AREGCIK")
        or company_name_tag.get("aregcik")
    )

    document_type = _detect_document_type(
        document_name,
    )

    if (
        document_type
        is AuditReportDocumentType.AUDIT_REPORT
        and not _looks_like_full_audit_report(soup)
    ):
        document_type = AuditReportDocumentType.UNKNOWN

    if (
        document_type
        is AuditReportDocumentType.BUSINESS_REPORT
        and not _has_audit_section(soup)
    ):
        document_type = AuditReportDocumentType.UNKNOWN

    return AuditReportDocument(
        document_code=str(document_code),
        document_name=document_name,
        document_type=document_type,
        company_name=company_name,
        company_code=(
            str(company_code)
            if company_code
            else None
        ),
        xml_text=xml_text,
    )


def parse_audit_report_html(
    html_text: str,
    *,
    document_name: str = "감사보고서",
    company_name: str = "",
    document_code: str = "",
    company_code: str | None = None,
) -> AuditReportDocument:
    """
    Playwright로 렌더링한 감사보고서 HTML을 판별한다.

    렌더링 HTML에는 DOCUMENT-NAME, COMPANY-NAME 같은 원본
    XML 메타데이터가 없을 수 있으므로 호출자가 이미 알고 있는
    첨부문서 정보는 선택 인자로 전달한다.
    """
    if not html_text.strip():
        raise ValueError(
            "감사보고서 HTML 내용이 비어 있습니다."
        )

    soup = BeautifulSoup(
        html_text,
        "html.parser",
    )

    document_type = _detect_document_type(
        document_name,
    )

    if not _looks_like_full_audit_report(soup):
        document_type = AuditReportDocumentType.UNKNOWN

    return AuditReportDocument(
        document_code=document_code,
        document_name=document_name,
        document_type=document_type,
        company_name=company_name,
        company_code=company_code,
        xml_text=html_text,
    )