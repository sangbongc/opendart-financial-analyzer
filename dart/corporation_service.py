from datetime import datetime
from io import BytesIO
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from dart.client import DartClient
from database.corporation_repository import (
    deactivate_missing_corporations,
    upsert_corporations,
)


class CorporationSyncError(Exception):
    """기업 고유번호 동기화 과정에서 발생하는 예외입니다."""


def _clean_text(value: str | None) -> str | None:
    """
    XML에서 읽은 문자열의 앞뒤 공백을 제거한다.

    빈 문자열은 None으로 변환한다.
    """
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _extract_xml_from_zip(zip_content: bytes) -> bytes:
    """
    OpenDART에서 받은 ZIP 바이너리에서 XML 파일을 추출한다.
    """
    try:
        with ZipFile(BytesIO(zip_content)) as zip_file:
            xml_filenames = [
                filename
                for filename in zip_file.namelist()
                if filename.lower().endswith(".xml")
            ]

            if not xml_filenames:
                raise CorporationSyncError(
                    "ZIP 파일 안에서 XML 파일을 찾을 수 없습니다."
                )

            return zip_file.read(xml_filenames[0])

    except BadZipFile as error:
        raise CorporationSyncError(
            "OpenDART 응답이 정상적인 ZIP 파일이 아닙니다."
        ) from error


def _parse_corporations(xml_content: bytes) -> list[dict]:
    """
    기업 고유번호 XML을 파싱하여 Repository가 받을 수 있는
    딕셔너리 목록으로 변환한다.
    """
    try:
        root = ET.fromstring(xml_content)

    except ET.ParseError as error:
        raise CorporationSyncError(
            "기업 고유번호 XML 파싱에 실패했습니다."
        ) from error

    corporations: list[dict] = []

    for element in root.findall("list"):
        corp_code = _clean_text(
            element.findtext("corp_code")
        )
        corp_name = _clean_text(
            element.findtext("corp_name")
        )
        stock_code = _clean_text(
            element.findtext("stock_code")
        )
        modify_date = _clean_text(
            element.findtext("modify_date")
        )

        if not corp_code or not corp_name:
            continue

        corporations.append(
            {
                "corp_code": corp_code,
                "corp_name": corp_name,
                "stock_code": stock_code,
                "modify_date": modify_date,
            }
        )

    if not corporations:
        raise CorporationSyncError(
            "XML에서 기업 정보를 한 건도 찾지 못했습니다."
        )

    return corporations


def sync_corporations(
    client: DartClient | None = None,
) -> dict:
    """
    OpenDART 기업 고유번호 목록을 내려받아 DB와 동기화한다.

    처리 순서
    1. ZIP 다운로드
    2. XML 추출
    3. 기업 목록 파싱
    4. 기업 저장 또는 갱신
    5. 최신 목록에 없는 기존 기업 비활성화
    """
    dart_client = client or DartClient()

    zip_content = dart_client.get_binary(
    "/corpCode.xml"
)
    xml_content = _extract_xml_from_zip(zip_content)
    corporations = _parse_corporations(xml_content)

    sync_time = datetime.now().isoformat(
        sep=" ",
        timespec="seconds",
    )

    saved_count = upsert_corporations(
        corporations=corporations,
        seen_at=sync_time,
    )

    active_corp_codes = [
        corporation["corp_code"]
        for corporation in corporations
    ]

    deactivated_count = deactivate_missing_corporations(
        active_corp_codes=active_corp_codes,
        deactivated_at=sync_time,
    )

    listed_count = sum(
        1
        for corporation in corporations
        if corporation["stock_code"] is not None
    )

    return {
        "received_count": len(corporations),
        "saved_count": saved_count,
        "listed_count": listed_count,
        "unlisted_count": len(corporations) - listed_count,
        "deactivated_count": deactivated_count,
        "synced_at": sync_time,
    }