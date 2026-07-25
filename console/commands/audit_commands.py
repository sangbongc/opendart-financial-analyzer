from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from audit.audit_KAM_parser import parse_key_audit_matters
from audit.audit_emphasis_parser import parse_emphasis_of_matter
from audit.audit_going_concern_parser import (
    parse_going_concern_uncertainty,
)
from audit.audit_opinion_parser import parse_audit_opinion
from audit.audit_other_matter_parser import parse_other_matter
from audit.audit_report_parser import parse_audit_report_html
from console.commands.corporation_commands import input_business_year
from dart.audit_report_file_service import (
    AuditReportDisclosure,
    AuditReportFileError,
    download_audit_report_attachment,
    fetch_audit_report_attachments,
    search_audit_reports,
)
from dart.audit_report_viewer_parser import AuditReportAttachment


OUTPUT_DIR = Path("data/audit_reports")
SEPARATOR_WIDTH = 70

REASON_BODY_START_PATTERNS = (
    re.compile(r"연결회사의\s+"),
    re.compile(r"회사의\s+"),
    re.compile(r"당사의\s+"),
    re.compile(r"연결회사는\s+"),
    re.compile(r"회사는\s+"),
    re.compile(r"당사는\s+"),
    re.compile(r"우리는\s+"),
    re.compile(r"본인은\s+"),
    re.compile(r"감사인은\s+"),
    re.compile(r"경영진은\s+"),
    re.compile(r"20\d{2}년\s+"),
)


def handle_audit_report(
    corporation_selector: Callable[[], dict | None],
) -> None:
    """
    기업과 사업연도를 입력받아 감사보고서 공시를 선택하고,
    첨부문서를 다운로드한 뒤 주요 감사 단락을 파싱하여 출력한다.
    """
    corporation = corporation_selector()

    if corporation is None:
        return

    business_year = input_business_year()
    start_date, end_date = _audit_report_search_period(
        business_year
    )

    corp_code = str(corporation["corp_code"])
    corp_name = str(corporation["corp_name"])

    print()
    print("[감사보고서 공시 검색]")
    print("-" * SEPARATOR_WIDTH)
    print(f"기업명: {corp_name}")
    print(f"기업 고유번호: {corp_code}")
    print(f"사업연도: {business_year}")
    print(
        "공시 검색 기간: "
        f"{_format_date(start_date)} ~ {_format_date(end_date)}"
    )

    try:
        disclosures = search_audit_reports(
            corp_code=corp_code,
            start_date=start_date,
            end_date=end_date,
        )

        disclosure = _select_disclosure(disclosures)

        attachments = fetch_audit_report_attachments(
            rcept_no=disclosure.rcept_no,
        )

        attachment = _select_attachment(attachments)

        print()
        print("[감사보고서 다운로드]")
        print("-" * SEPARATOR_WIDTH)
        print(f"공시명: {disclosure.report_name}")
        print(f"접수일자: {_format_date(disclosure.rcept_date)}")
        print(f"접수번호: {disclosure.rcept_no}")
        print(f"문서명: {attachment.title}")
        print(
            "문서 유형: "
            f"{'연결' if attachment.is_consolidated else '별도'}"
        )

        document_text = download_audit_report_attachment(
            attachment=attachment,
        )

        if not document_text.strip():
            raise AuditReportFileError(
                "다운로드한 감사보고서 본문이 비어 있습니다."
            )

        output_path = _save_audit_report(
            document_text=document_text,
            rcept_no=attachment.rcept_no,
            title=attachment.title,
        )

        print(f"다운로드 문자 수: {len(document_text):,}자")
        print(f"저장 경로: {output_path.resolve()}")

        document = parse_audit_report_html(
            document_text,
            document_name=attachment.title,
            company_name=corp_name,
            company_code=corp_code,
            document_code=attachment.dcm_no,
        )

        _print_document_information(document)
        _print_opinion(document.xml_text)
        _print_key_audit_matters(document.xml_text)
        _print_emphasis_of_matter(document.xml_text)
        _print_other_matter(document.xml_text)
        _print_going_concern(document.xml_text)

    except (
        AuditReportFileError,
        ValueError,
        RuntimeError,
        AssertionError,
    ) as error:
        print()
        print("[감사보고서 분석 실패]")
        print("-" * SEPARATOR_WIDTH)
        print(f"{type(error).__name__}: {error}")


def _audit_report_search_period(
    business_year: str,
) -> tuple[str, str]:
    """
    입력한 사업연도의 다음 해 전체를 공시 검색 기간으로 반환한다.

    예:
        사업연도 2025
        -> 20260101 ~ 20261231
    """
    filing_year = int(business_year) + 1
    return f"{filing_year}0101", f"{filing_year}1231"


def _select_disclosure(
    disclosures: list[AuditReportDisclosure],
) -> AuditReportDisclosure:
    """검색된 감사보고서 관련 공시 중 하나를 선택한다."""
    if not disclosures:
        raise AuditReportFileError(
            "해당 기간에 감사보고서 관련 공시가 없습니다."
        )

    print()
    print("[감사보고서 공시 후보]")
    print("-" * SEPARATOR_WIDTH)

    for index, disclosure in enumerate(
        disclosures,
        start=1,
    ):
        print(
            f"{index}. "
            f"{_format_date(disclosure.rcept_date)} | "
            f"{disclosure.report_name}"
        )
        print(
            f"   접수번호: {disclosure.rcept_no} | "
            f"제출인: {disclosure.filer_name or '-'}"
        )

    if len(disclosures) == 1:
        print()
        print("검색 결과가 1건이므로 자동 선택합니다.")
        return disclosures[0]

    selected_index = _read_selection(
        prompt="\n분석할 공시 번호를 입력하세요: ",
        item_count=len(disclosures),
    )
    return disclosures[selected_index]


def _select_attachment(
    attachments: list[AuditReportAttachment],
) -> AuditReportAttachment:
    """공시의 연결·별도 감사보고서 첨부문서 중 하나를 선택한다."""
    if not attachments:
        raise AuditReportFileError(
            "선택할 감사보고서 첨부문서가 없습니다."
        )

    print()
    print("[감사보고서 첨부문서]")
    print("-" * SEPARATOR_WIDTH)

    for index, attachment in enumerate(
        attachments,
        start=1,
    ):
        report_type = (
            "연결"
            if attachment.is_consolidated
            else "별도"
        )
        print(
            f"{index}. {report_type} | "
            f"{attachment.title} | "
            f"dcmNo={attachment.dcm_no}"
        )

    if len(attachments) == 1:
        print()
        print("첨부문서가 1건이므로 자동 선택합니다.")
        return attachments[0]

    selected_index = _read_selection(
        prompt="\n분석할 첨부문서 번호를 입력하세요: ",
        item_count=len(attachments),
    )
    return attachments[selected_index]


def _read_selection(
    prompt: str,
    item_count: int,
) -> int:
    """1부터 item_count까지의 번호를 입력받아 0 기반 인덱스로 반환한다."""
    while True:
        value = input(prompt).strip()

        try:
            selected_index = int(value) - 1
        except ValueError:
            print("숫자로 입력해야 합니다.")
            continue

        if not 0 <= selected_index < item_count:
            print("목록에 있는 번호를 입력하세요.")
            continue

        return selected_index


def _safe_filename(value: str) -> str:
    """Windows에서도 저장 가능한 파일명으로 정리한다."""
    normalized = " ".join(value.split()).strip()
    normalized = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        normalized,
    )
    return normalized or "audit_report"


def _save_audit_report(
    document_text: str,
    rcept_no: str,
    title: str,
) -> Path:
    """다운로드한 감사보고서 전문을 UTF-8 HTML 파일로 저장한다."""
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"{rcept_no}_"
        f"{_safe_filename(title)}.html"
    )
    output_path = OUTPUT_DIR / filename

    output_path.write_text(
        document_text,
        encoding="utf-8",
    )

    if output_path.stat().st_size == 0:
        raise AuditReportFileError(
            "저장된 감사보고서 파일이 비어 있습니다."
        )

    return output_path


def _print_document_information(
    document: object,
) -> None:
    print()
    print("[감사보고서 문서 정보]")
    print("-" * SEPARATOR_WIDTH)
    print(f"문서 유형: {document.document_type.value}")
    print(f"문서명: {document.document_name}")
    print(f"회사명: {document.company_name}")


def _print_opinion(xml_text: str) -> None:
    opinion = parse_audit_opinion(xml_text)

    print()
    print("[감사의견]")
    print("-" * SEPARATOR_WIDTH)
    print(f"감사의견 유형: {opinion.opinion_type}")
    print(f"감사의견 제목: {opinion.heading}")

    print()
    print("[감사의견 본문]")
    print("-" * SEPARATOR_WIDTH)
    print(opinion.opinion_text or "-")

    if opinion.basis_heading:
        print()
        print(f"[{opinion.basis_heading}]")
        print("-" * SEPARATOR_WIDTH)
        print(opinion.opinion_basis_text or "-")

    if not opinion.basis_reasons:
        return

    print()
    print("[감사의견 근거 세부 사유]")
    print("-" * SEPARATOR_WIDTH)

    for index, reason in enumerate(
        opinion.basis_reasons,
        start=1,
    ):
        title, body = _split_reason_title_and_body(
            reason
        )

        print(f"{index}. {title}")

        if body:
            print(body)

        print()


def _split_reason_title_and_body(
    reason: str,
) -> tuple[str, str]:
    """감사의견 근거 사유를 제목과 본문으로 나눈다."""
    normalized = re.sub(
        r"\s+",
        " ",
        reason,
    ).strip()

    candidates: list[re.Match[str]] = []

    for pattern in REASON_BODY_START_PATTERNS:
        match = pattern.search(normalized)

        if match is None or match.start() == 0:
            continue

        candidates.append(match)

    if not candidates:
        return normalized, ""

    first_match = min(
        candidates,
        key=lambda item: item.start(),
    )

    split_index = first_match.start()

    return (
        normalized[:split_index].strip(),
        normalized[split_index:].strip(),
    )


def _print_key_audit_matters(
    xml_text: str,
) -> None:
    key_audit_matters = parse_key_audit_matters(
        xml_text
    )

    print()
    print("[핵심감사사항]")
    print("-" * SEPARATOR_WIDTH)

    if key_audit_matters is None:
        print("핵심감사사항을 찾지 못했습니다.")
        return

    print(
        "핵심감사사항 제목: "
        f"{key_audit_matters.heading}"
    )

    if key_audit_matters.introduction_text:
        print()
        print("[공통 설명]")
        print("-" * SEPARATOR_WIDTH)
        print(
            key_audit_matters.introduction_text
        )

    if not key_audit_matters.matters:
        print()
        print("개별 핵심감사사항이 없습니다.")
        return

    for index, matter in enumerate(
        key_audit_matters.matters,
        start=1,
    ):
        print()
        print(f"[핵심감사사항 {index}]")
        print("-" * SEPARATOR_WIDTH)

        if matter.title:
            print(f"제목: {matter.title}")
            print()

        print(matter.text)


def _print_emphasis_of_matter(
    xml_text: str,
) -> None:
    emphasis = parse_emphasis_of_matter(
        xml_text
    )

    print()
    print("[강조사항]")
    print("-" * SEPARATOR_WIDTH)

    if emphasis is None:
        print("강조사항이 없습니다.")
        return

    print(f"제목: {emphasis.heading}")
    print()
    print(emphasis.text)


def _print_other_matter(
    xml_text: str,
) -> None:
    other_matter = parse_other_matter(
        xml_text
    )

    print()
    print("[기타사항]")
    print("-" * SEPARATOR_WIDTH)

    if other_matter is None:
        print("기타사항이 없습니다.")
        return

    print(f"제목: {other_matter.heading}")
    print()
    print(other_matter.text)


def _print_going_concern(
    xml_text: str,
) -> None:
    going_concern = (
        parse_going_concern_uncertainty(
            xml_text
        )
    )

    print()
    print("[계속기업 관련 중요한 불확실성]")
    print("-" * SEPARATOR_WIDTH)

    if going_concern is None:
        print(
            "계속기업 관련 중요한 "
            "불확실성이 없습니다."
        )
        return

    print(f"제목: {going_concern.heading}")
    print()
    print(going_concern.text)


def _format_date(value: str) -> str:
    """YYYYMMDD 문자열을 YYYY-MM-DD로 표시한다."""
    if len(value) == 8 and value.isdigit():
        return (
            f"{value[:4]}-"
            f"{value[4:6]}-"
            f"{value[6:]}"
        )

    return value