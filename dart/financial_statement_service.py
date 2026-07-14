from typing import Any

from .client import DartClient
from .financial_statement_parser import (
    parse_financial_statement_response,
)
from database.financial_statement_repository import (
    save_financial_statements,
)


DEFAULT_REPORT_CODE = "11011"
DEFAULT_FS_DIV = "CFS"


def fetch_financial_statements_from_dart(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = DEFAULT_REPORT_CODE,
    fs_div: str = DEFAULT_FS_DIV,
    client: DartClient | None = None,
) -> list[dict[str, Any]]:
    """
    DART에서 특정 기업의 재무제표를 조회한다.

    Parameters
    ----------
    corp_code
        DART 기업고유번호

    bsns_year
        사업연도

    reprt_code
        보고서 코드
        11011 : 사업보고서
        11012 : 반기보고서
        11013 : 1분기보고서
        11014 : 3분기보고서

    fs_div
        CFS : 연결재무제표
        OFS : 별도재무제표
    """

    dart_client = client or DartClient()

    response = dart_client.get(
        "fnlttSinglAcntAll.json",
        {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        },
    )

    return parse_financial_statement_response(
        response
        )


def sync_financial_statements(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = DEFAULT_REPORT_CODE,
    fs_div: str = DEFAULT_FS_DIV,
    client: DartClient | None = None,
) -> dict:
    """
    DART에서 재무제표를 조회하여 DB에 저장한다.
    """

    financial_statements = fetch_financial_statements_from_dart(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
        client=client,
    )

    saved_count = save_financial_statements(
        financial_statements
    )

    return {
        "received_count": len(financial_statements),
        "saved_count": saved_count,
        "ignored_count": (
            len(financial_statements) - saved_count
        ),
    }