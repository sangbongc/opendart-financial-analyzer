from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from audit.audit_opinion_parser import parse_audit_opinion
from audit.audit_report_parser import parse_audit_report_html
from dart.audit_report_file_service import (
    AuditReportFileError,
    download_audit_report_attachment,
    fetch_audit_report_attachments,
    search_audit_reports,
    select_audit_report_attachment,
    select_latest_audit_report,
)

# False: 별도 감사보고서
# True: 연결감사보고서
# None: 연결이 있으면 연결, 없으면 별도
CONSOLIDATED: bool | None = None

OUTPUT_DIR = Path("data/audit_reports")
SEARCH_YEARS = 3


def _safe_filename(value: str) -> str:
    """Windows에서도 저장 가능한 파일명으로 정리한다."""
    normalized = " ".join(value.split()).strip()
    normalized = re.sub(r'[\\/:*?"<>|]', "_", normalized)
    return normalized or "audit_report"


def _save_audit_report(
    document_text: str,
    rcept_no: str,
    title: str,
    dtd: str,
) -> Path:
    """다운로드한 감사보고서 전문을 UTF-8 파일로 저장한다."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extension = ".xml" if dtd.upper() == "XML" else ".html"
    filename = f"{rcept_no}_{_safe_filename(title)}{extension}"
    output_path = OUTPUT_DIR / filename
    output_path.write_text(document_text, encoding="utf-8")
    return output_path


def _read_corp_code() -> str:
    corp_code = input("기업 고유번호 8자리를 입력하세요: ").strip()

    if len(corp_code) != 8 or not corp_code.isdigit():
        raise ValueError(
            "기업 고유번호는 숫자 8자리여야 합니다."
        )

    return corp_code


def _search_period() -> tuple[str, str]:
    today = date.today()
    start_date = f"{today.year - SEARCH_YEARS}0101"
    end_date = today.strftime("%Y%m%d")
    return start_date, end_date


def main() -> None:
    load_dotenv()

    corp_code = _read_corp_code()
    start_date, end_date = _search_period()

    print()
    print("[1. 최신 감사보고서 공시 검색]")
    print("-" * 70)
    print(f"기업 고유번호: {corp_code}")
    print(f"검색 기간: {start_date} ~ {end_date}")

    disclosures = search_audit_reports(
        corp_code=corp_code,
        start_date=start_date,
        end_date=end_date,
    )
    disclosure = select_latest_audit_report(disclosures)

    print(f"회사명: {disclosure.corp_name}")
    print(f"공시명: {disclosure.report_name}")
    print(f"접수번호: {disclosure.rcept_no}")
    print(f"접수일자: {disclosure.rcept_date}")
    print(f"제출인: {disclosure.filer_name}")

    print()
    print("[2. 감사보고서 첨부문서 조회]")
    print("-" * 70)

    attachments = fetch_audit_report_attachments(
        rcept_no=disclosure.rcept_no,
    )

    print(f"감사보고서 첨부문서: {len(attachments)}건")

    for index, attachment in enumerate(attachments, start=1):
        report_type = "연결" if attachment.is_consolidated else "별도"
        print(
            f"{index}. {report_type} | "
            f"{attachment.title} | "
            f"dcmNo={attachment.dcm_no}"
        )

    selected_attachment = select_audit_report_attachment(
        attachments=attachments,
        consolidated=CONSOLIDATED,
    )

    print()
    print("[3. 선택된 감사보고서 첨부문서]")
    print("-" * 70)
    print(f"문서명: {selected_attachment.title}")
    print(
        "문서 유형: "
        f"{'연결' if selected_attachment.is_consolidated else '별도'}"
    )
    print(f"rcpNo: {selected_attachment.rcept_no}")
    print(f"dcmNo: {selected_attachment.dcm_no}")

    print()
    print("[4. 감사보고서 전문 다운로드]")
    print("-" * 70)

    document_text = download_audit_report_attachment(
        attachment=selected_attachment,
    )

    if not document_text.strip():
        raise AssertionError(
            "다운로드한 감사보고서 본문이 비어 있습니다."
        )

    print(f"다운로드 문자 수: {len(document_text):,}자")

    output_path = _save_audit_report(
        document_text=document_text,
        rcept_no=selected_attachment.rcept_no,
        title=selected_attachment.title,
        dtd=selected_attachment.dtd,
    )

    if output_path.stat().st_size == 0:
        raise AssertionError(
            "저장된 감사보고서 파일이 비어 있습니다."
        )

    print(f"저장 경로: {output_path.resolve()}")

    print()
    print("[5. 감사보고서 문서 판별]")
    print("-" * 70)

    document = parse_audit_report_html(
        document_text,
        document_name=selected_attachment.title,
        company_name=disclosure.corp_name,
        company_code=corp_code,
        document_code=selected_attachment.dcm_no,
    )

    print(f"문서 유형: {document.document_type.value}")
    print(f"문서명: {document.document_name}")
    print(f"회사명: {document.company_name}")

    print()
    print("[6. 감사의견 파싱]")
    print("-" * 70)

    opinion = parse_audit_opinion(document.xml_text)

    print(f"감사의견 유형: {opinion.opinion_type}")
    print(f"감사의견 제목: {opinion.heading}")

    print()
    print("[감사의견 본문]")
    print("-" * 70)
    print(opinion.opinion_text)

    if opinion.basis_heading:
        print()
        print(f"[{opinion.basis_heading}]")
        print("-" * 70)
        print(opinion.opinion_basis_text or "-")
    else:
        print()
        print("감사의견 근거 단락: 없음")

    print()
    print("[통합 테스트 성공]")
    print("-" * 70)
    print(
        "기업 고유번호 입력 → 최신 감사보고서 공시 검색 → "
        "첨부문서 선택 → 본문 다운로드 → 저장 → "
        "문서 판별 → 감사의견 파싱 완료"
    )


if __name__ == "__main__":
    try:
        main()
    except (
        AuditReportFileError,
        ValueError,
        RuntimeError,
        AssertionError,
    ) as error:
        print()
        print("[통합 테스트 실패]")
        print("-" * 70)
        print(f"{type(error).__name__}: {error}")
        raise