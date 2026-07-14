from typing import Any

from .client import DartClient
from .financial_statement_parser import (
    parse_financial_statement_response,
)


DEFAULT_REPORT_CODE = "11011"
DEFAULT_FS_DIV = "CFS"


def fetch_financial_statements(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = DEFAULT_REPORT_CODE,
    fs_div: str = DEFAULT_FS_DIV,
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

    client = DartClient()

    response = client.get(
        "fnlttSinglAcntAll.json",
        {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        },
    )

    return parse_financial_statement_response(response)