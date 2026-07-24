import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


OPINION_FIELD_PATTERN = re.compile(
    r"^OPN_(?P<field>[A-Z]+)"
    r"(?P<year_index>\d+)"
    r"_(?P<report_suffix>[AC])$"
)

YEAR_PATTERN = re.compile(
    r"^OPN_YEAR(?P<year_index>\d+)$"
)

REPORT_TYPE_BY_SUFFIX = {
    "A": "감사보고서",
    "C": "연결감사보고서",
}

AUDIT_SECTION_HEADINGS = {
    "회계감사인의 감사의견 등",
    "회계감사인의 감사의견",
    "감사인의 감사의견 등",
    "감사인의 감사의견",
}

FIELD_NAME_MAP = {
    "AUR": "auditor_name",
    "CMT": "opinion_type",
    "RSN": "opinion_change_reason",
    "UCT": "going_concern_uncertainty",
    "EMP": "emphasis_matter",
    "POT": "key_audit_matter",
}


@dataclass(frozen=True)
class BusinessReportAuditOpinion:
    fiscal_year: str
    report_type: str
    auditor_name: str | None
    opinion_type: str | None
    opinion_change_reason: str | None
    going_concern_uncertainty: str | None
    emphasis_matter: str | None
    key_audit_matter: str | None


def _normalize_text(text: str) -> str:
    return "".join(text.split())


def _clean_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = " ".join(
        value.split()
    ).strip()

    if not normalized:
        return None

    compact = _normalize_text(normalized)

    if compact in {
        "-",
        "해당사항없음",
        "-해당사항없음.",
        "해당사항없음.",
    }:
        return None

    return normalized


def _find_audit_section(
    soup: BeautifulSoup,
) -> Tag | None:
    for section in soup.find_all("SECTION-1"):
        title = section.find(
            "TITLE",
            recursive=False,
        )

        if title is None:
            continue

        normalized_title = _normalize_text(
            title.get_text(" ", strip=True)
        )

        if any(
            _normalize_text(heading)
            in normalized_title
            for heading in AUDIT_SECTION_HEADINGS
        ):
            return section

    return None


def _collect_opinion_fields(
    audit_section: Tag,
) -> dict[
    tuple[int, str],
    dict[str, str | None],
]:
    records: dict[
        tuple[int, str],
        dict[str, str | None],
    ] = {}

    for tag in audit_section.find_all(True):
        code = (
            tag.get("ACODE")
            or tag.get("AUNIT")
        )

        if not code:
            continue

        match = OPINION_FIELD_PATTERN.fullmatch(
            str(code),
        )

        if match is None:
            continue

        field_name = match.group("field")

        if field_name not in FIELD_NAME_MAP:
            continue

        year_index = int(
            match.group("year_index")
        )
        report_suffix = match.group(
            "report_suffix"
        )

        key = (
            year_index,
            report_suffix,
        )

        records.setdefault(key, {})
        records[key][field_name] = _clean_text(
            tag.get_text(" ", strip=True)
        )

    return records


def _collect_fiscal_years(
    audit_section: Tag,
) -> dict[int, str]:
    fiscal_years: dict[int, str] = {}

    for tag in audit_section.find_all(True):
        acode = tag.get("ACODE")

        if not acode:
            continue

        match = YEAR_PATTERN.fullmatch(
            str(acode),
        )

        if match is None:
            continue

        year_index = int(
            match.group("year_index")
        )
        fiscal_year = _clean_text(
            tag.get_text(" ", strip=True)
        )

        if fiscal_year is not None:
            fiscal_years[year_index] = fiscal_year

    return fiscal_years


def parse_business_report_audit_opinions(
    xml_text: str,
) -> list[BusinessReportAuditOpinion]:
    if not xml_text.strip():
        raise ValueError(
            "사업보고서 XML 내용이 비어 있습니다."
        )

    soup = BeautifulSoup(
        xml_text,
        "xml",
    )

    audit_section = _find_audit_section(soup)

    if audit_section is None:
        raise ValueError(
            "사업보고서에서 '회계감사인의 "
            "감사의견 등' 섹션을 찾지 못했습니다."
        )

    fiscal_years = _collect_fiscal_years(
        audit_section,
    )
    fields_by_record = _collect_opinion_fields(
        audit_section,
    )

    results: list[BusinessReportAuditOpinion] = []

    for (
        year_index,
        report_suffix,
    ), fields in sorted(
        fields_by_record.items(),
        key=lambda item: (
            item[0][0],
            item[0][1],
        ),
    ):
        fiscal_year = fiscal_years.get(
            year_index,
        )

        if fiscal_year is None:
            continue

        results.append(
            BusinessReportAuditOpinion(
                fiscal_year=fiscal_year,
                report_type=(
                    REPORT_TYPE_BY_SUFFIX[
                        report_suffix
                    ]
                ),
                auditor_name=fields.get("AUR"),
                opinion_type=fields.get("CMT"),
                opinion_change_reason=fields.get(
                    "RSN"
                ),
                going_concern_uncertainty=fields.get(
                    "UCT"
                ),
                emphasis_matter=fields.get("EMP"),
                key_audit_matter=fields.get("POT"),
            )
        )

    if not results:
        raise ValueError(
            "사업보고서의 감사의견 섹션에서 "
            "정형 필드를 찾지 못했습니다."
        )

    return results