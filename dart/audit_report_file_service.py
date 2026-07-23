from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

from dart.client import (
    DartAPIError,
    DartClient,
)


AUDIT_REPORT_DETAIL_TYPES = (
    "F001",  # 감사보고서
    "F002",  # 연결감사보고서
)

DOCUMENT_API_URL = (
    "https://opendart.fss.or.kr/api/document.xml"
)


class AuditReportFileError(Exception):
    """
    감사보고서 검색 또는 원문 다운로드 중 발생하는 오류.
    """


@dataclass(frozen=True)
class AuditReportDisclosure:
    """
    OpenDART 공시검색에서 조회한 감사보고서 정보.
    """

    corp_code: str
    corp_name: str
    report_name: str
    rcept_no: str
    rcept_date: str
    filer_name: str


def search_annual_reports(
    corp_code: str,
    start_date: str,
    end_date: str,
) -> list[AuditReportDisclosure]:
    """
    지정한 기간의 사업보고서를 조회한다.
    """
    client = DartClient()

    try:
        response = client.get(
            "/list.json",
            {
                "corp_code": corp_code,
                "bgn_de": start_date,
                "end_de": end_date,
                "last_reprt_at": "Y",
                "pblntf_ty": "A",
                "pblntf_detail_ty": "A001",
                "sort": "date",
                "sort_mth": "desc",
                "page_no": "1",
                "page_count": "100",
            },
        )

    except DartAPIError as error:
        if error.status == "013":
            return []

        raise AuditReportFileError(
            "사업보고서 검색에 실패했습니다."
        ) from error

    disclosures = []

    for item in response.get("list", []):
        disclosures.append(
            AuditReportDisclosure(
                corp_code=str(item.get("corp_code") or ""),
                corp_name=str(item.get("corp_name") or ""),
                report_name=str(item.get("report_nm") or ""),
                rcept_no=str(item.get("rcept_no") or ""),
                rcept_date=str(item.get("rcept_dt") or ""),
                filer_name=str(item.get("flr_nm") or ""),
            )
        )

    return disclosures


def download_audit_report_zip(
    rcept_no: str,
    api_key: str,
    timeout: int = 30,
) -> bytes:
    """
    접수번호에 해당하는 공시서류 원본 ZIP을 다운로드한다.
    """
    if len(rcept_no) != 14 or not rcept_no.isdigit():
        raise ValueError(
            "접수번호는 숫자 14자리여야 합니다."
        )

    try:
        response = requests.get(
            DOCUMENT_API_URL,
            params={
                "crtfc_key": api_key,
                "rcept_no": rcept_no,
            },
            timeout=timeout,
        )
        response.raise_for_status()

    except requests.RequestException as error:
        raise AuditReportFileError(
            "감사보고서 원문 다운로드 요청에 "
            "실패했습니다."
        ) from error

    content = response.content

    if not content:
        raise AuditReportFileError(
            "다운로드한 감사보고서 파일이 비어 있습니다."
        )

    if not zipfile.is_zipfile(io.BytesIO(content)):
        message = _extract_error_message(content)

        raise AuditReportFileError(
            "OpenDART가 ZIP 파일을 반환하지 않았습니다. "
            f"{message}"
        )

    return content


def _extract_error_message(content: bytes) -> str:
    """
    ZIP 대신 반환된 OpenDART 오류 XML을 문자열로 변환한다.
    """
    try:
        text = content.decode(
            "utf-8",
            errors="replace",
        )
    except Exception:
        return "응답 내용을 확인할 수 없습니다."

    compact_text = " ".join(text.split())

    if len(compact_text) > 300:
        return compact_text[:300] + "..."

    return compact_text


def save_audit_report_zip(
    zip_content: bytes,
    rcept_no: str,
    output_dir: str | Path,
) -> Path:
    """
    다운로드한 감사보고서 ZIP 파일을 저장한다.
    """
    directory = Path(output_dir)
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = directory / f"{rcept_no}.zip"
    output_path.write_bytes(zip_content)

    return output_path


def list_document_files(
    zip_content: bytes,
) -> list[str]:
    """
    공시 원문 ZIP 내부의 파일명 목록을 반환한다.
    """
    with zipfile.ZipFile(
        io.BytesIO(zip_content)
    ) as archive:
        return archive.namelist()


def read_document_text(
    zip_content: bytes,
    filename: str | None = None,
) -> str:
    """
    공시 원문 ZIP 내부 문서를 문자열로 읽는다.
    """
    with zipfile.ZipFile(
        io.BytesIO(zip_content)
    ) as archive:
        filenames = archive.namelist()

        if not filenames:
            raise AuditReportFileError(
                "공시 원문 ZIP 내부에 파일이 없습니다."
            )

        selected_filename = filename or filenames[0]
        document_content = archive.read(
            selected_filename
        )

    for encoding in (
        "utf-8",
        "euc-kr",
        "cp949",
    ):
        try:
            return document_content.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise AuditReportFileError(
        "공시 원문 문서의 문자 인코딩을 "
        "확인할 수 없습니다."
    )