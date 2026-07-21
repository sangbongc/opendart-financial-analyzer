from io import BytesIO
from zipfile import BadZipFile, ZipFile

from dart.client import DartClient
from dart.disclosure_service import (
    find_financial_report_rcept_no,
)


class XbrlFileDownloadError(Exception):
    """
    XBRL 원본 파일 다운로드에 실패했을 때 발생한다.
    """


class XbrlArchiveError(Exception):
    """
    다운로드한 XBRL 파일이 정상적인 ZIP 형식이 아닐 때 발생한다.
    """


def download_xbrl_archive(
    rcept_no: str,
    reprt_code: str,
) -> bytes:
    """
    OpenDART에서 재무제표 원본 XBRL ZIP 파일을 다운로드한다.

    Args:
        rcept_no:
            공시 접수번호.

        reprt_code:
            보고서 코드.
            예:
            - 11011: 사업보고서
            - 11012: 반기보고서
            - 11013: 1분기보고서
            - 11014: 3분기보고서

    Returns:
        다운로드한 ZIP 파일의 바이너리 데이터.

    Raises:
        ValueError:
            필수 입력값이 비어 있는 경우.

        XbrlFileDownloadError:
            API 호출 또는 파일 다운로드에 실패한 경우.

        XbrlArchiveError:
            응답이 정상적인 ZIP 파일이 아닌 경우.
    """
    if not rcept_no.strip():
        raise ValueError(
            "접수번호를 입력해야 합니다."
        )

    if not reprt_code.strip():
        raise ValueError(
            "보고서 코드를 입력해야 합니다."
        )

    client = DartClient()

    try:
        content = client.download(
            "/fnlttXbrl.xml",
            {
                "rcept_no": rcept_no,
                "reprt_code": reprt_code,
            },
        )

    except Exception as error:
        raise XbrlFileDownloadError(
            f"XBRL 파일 다운로드에 실패했습니다: {error}"
        ) from error

    if not content:
        raise XbrlFileDownloadError(
            "XBRL 파일 응답이 비어 있습니다."
        )

    if not _is_zip_archive(content):
        raise XbrlArchiveError(
            "OpenDART 응답이 정상적인 XBRL ZIP 파일이 아닙니다."
        )

    return content


def get_xbrl_archive_file_names(
    content: bytes,
) -> list[str]:
    """
    XBRL ZIP 파일 안에 포함된 파일명 목록을 반환한다.

    디렉터리 항목은 제외하고 실제 파일만 반환한다.

    Args:
        content:
            XBRL ZIP 파일의 바이너리 데이터.

    Returns:
        ZIP 내부 파일명 목록.

    Raises:
        XbrlArchiveError:
            정상적인 ZIP 파일이 아니거나 압축파일을 읽지 못한 경우.
    """
    if not content:
        raise XbrlArchiveError(
            "XBRL ZIP 파일 데이터가 비어 있습니다."
        )

    try:
        with ZipFile(BytesIO(content)) as archive:
            return [
                info.filename
                for info in archive.infolist()
                if not info.is_dir()
            ]

    except BadZipFile as error:
        raise XbrlArchiveError(
            "XBRL ZIP 파일을 읽을 수 없습니다."
        ) from error


def download_and_inspect_xbrl(
    rcept_no: str,
    reprt_code: str,
) -> list[str]:
    """
    XBRL 원본 파일을 다운로드하고 ZIP 내부 파일명 목록을 반환한다.
    """
    content = download_xbrl_archive(
        rcept_no=rcept_no,
        reprt_code=reprt_code,
    )

    return get_xbrl_archive_file_names(content)


def _is_zip_archive(content: bytes) -> bool:
    """
    주어진 바이너리 데이터가 ZIP 파일인지 확인한다.

    ZIP 파일의 일반적인 매직 바이트인 PK로 시작하는지 우선 확인하고,
    실제로 ZipFile에서 열 수 있는지도 검사한다.
    """
    if not content.startswith(b"PK"):
        return False

    try:
        with ZipFile(BytesIO(content)) as archive:
            return archive.testzip() is None

    except BadZipFile:
        return False
    

def download_xbrl_archive_by_report(
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
) -> bytes:
    """
    기업과 사업연도 기준으로 접수번호를 조회한 뒤
    XBRL 원본 ZIP 파일을 다운로드한다.
    """
    rcept_no = find_financial_report_rcept_no(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
    )

    if rcept_no is None:
        raise XbrlFileDownloadError(
            "조건에 해당하는 정기공시를 찾을 수 없습니다."
        )

    return download_xbrl_archive(
        rcept_no=rcept_no,
        reprt_code=reprt_code,
    )