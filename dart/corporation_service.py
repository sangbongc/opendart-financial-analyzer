from datetime import datetime
from io import BytesIO
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from dart.client import DartClient
from database.corporation_repository import (
    deactivate_missing_corporations,
    upsert_corporations,
    search_corporations_by_name,
    fetch_corporation_by_corp_code,
    fetch_corporation_by_stock_code,
    count_corporations_by_keyword,
)


class CorporationSyncError(Exception):
    """기업 고유번호 동기화 과정에서 발생하는 예외입니다."""


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


def find_corporations(
    query: str,
    active_only: bool = True,
    limit: int = 20,
) -> list[dict]:
    """
    종목코드, DART 기업 고유번호 또는 기업명으로 기업을 찾는다.

    - 숫자 6자리: 주식 종목코드로 조회
    - 숫자 8자리: DART 기업 고유번호로 조회
    - 그 외 입력: 기업명 부분 검색

    반환 형식을 일관되게 유지하기 위해 항상 목록을 반환한다.
    """
    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError(
            "기업 검색어는 비어 있을 수 없습니다."
        )

    if _is_stock_code(normalized_query):
        corporation = fetch_corporation_by_stock_code(
            stock_code=normalized_query,
            active_only=active_only,
        )

        if corporation is None:
            return []

        return [corporation]

    if _is_corp_code(normalized_query):
        corporation = fetch_corporation_by_corp_code(
            corp_code=normalized_query,
        )

        if corporation is None:
            return []

        if active_only and not corporation["is_active"]:
            return []

        return [corporation]

    return search_corporations_by_name(
        keyword=normalized_query,
        active_only=active_only,
        limit=limit,
    )


def find_corporations_with_count(
    keyword: str,
    limit: int = 20,
) -> dict:
    normalized_keyword = keyword.strip()

    corporations = find_corporations(
        query=normalized_keyword,
        limit=limit,
    )

    if (
        _is_stock_code(normalized_keyword)
        or _is_corp_code(normalized_keyword)
    ):
        total_count = len(corporations)

    else:
        total_count = count_corporations_by_keyword(
            normalized_keyword,
        )

    return {
        "corporations": corporations,
        "total_count": total_count,
    }


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


def _is_stock_code(value: str) -> bool:
    """
    입력값이 6자리 주식 종목코드 형식인지 확인한다.
    """
    return len(value) == 6 and value.isdigit()


def _is_corp_code(value: str) -> bool:
    """
    입력값이 8자리 DART 기업 고유번호 형식인지 확인한다.
    """
    return len(value) == 8 and value.isdigit()

