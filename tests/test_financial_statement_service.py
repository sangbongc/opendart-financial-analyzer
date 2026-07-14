from unittest.mock import Mock
from unittest.mock import patch

from dart.financial_statement_service import (
    fetch_financial_statements_from_dart,
    sync_financial_statements,
)


@patch("dart.financial_statement_service.parse_financial_statement_response")
@patch("dart.financial_statement_service.DartClient")
def test_fetch_financial_statements(
    mock_client_class: Mock,
    mock_parser: Mock,
):
    client = Mock()

    mock_client_class.return_value = client

    client.get.return_value = {
        "status": "000",
        "list": [],
    }

    mock_parser.return_value = [
        {
            "account_nm": "매출액",
        }
    ]

    result = fetch_financial_statements_from_dart(
        corp_code="00126380",
        bsns_year="2025",
    )

    client.get.assert_called_once_with(
        "fnlttSinglAcntAll.json",
        {
            "corp_code": "00126380",
            "bsns_year": "2025",
            "reprt_code": "11011",
            "fs_div": "CFS",
        },
    )

    mock_parser.assert_called_once()

    assert result == [
        {
            "account_nm": "매출액",
        }
    ]

SAMPLE_API_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {
            "rcept_no": "20260317001234",
            "reprt_code": "11011",
            "bsns_year": "2025",
            "corp_code": "00126380",
            "fs_div": "CFS",
            "fs_nm": "연결재무제표",
            "sj_div": "BS",
            "sj_nm": "재무상태표",
            "account_id": "ifrs-full_Assets",
            "account_nm": "자산총계",
            "account_detail": "-",
            "thstrm_nm": "제57기",
            "thstrm_amount": "500000000000000",
            "currency": "KRW",
        }
    ],
}


PARSED_FINANCIAL_STATEMENTS = [
    {
        "rcept_no": "20260317001234",
        "reprt_code": "11011",
        "bsns_year": "2025",
        "corp_code": "00126380",
        "fs_div": "CFS",
        "fs_nm": "연결재무제표",
        "sj_div": "BS",
        "sj_nm": "재무상태표",
        "account_id": "ifrs-full_Assets",
        "account_nm": "자산총계",
        "account_detail": "-",
        "thstrm_nm": "제57기",
        "thstrm_amount": 500000000000000,
        "currency": "KRW",
    }
]


@patch(
    "dart.financial_statement_service."
    "parse_financial_statement_response"
)
def test_fetch_financial_statements_from_dart(
    mock_parse: Mock,
):
    """
    DART API 응답이 파서에 전달되고,
    파싱 결과가 그대로 반환되는지 확인한다.
    """
    mock_client = Mock()
    mock_client.get.return_value = SAMPLE_API_RESPONSE
    mock_parse.return_value = PARSED_FINANCIAL_STATEMENTS

    result = fetch_financial_statements_from_dart(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        client=mock_client,
    )

    assert result == PARSED_FINANCIAL_STATEMENTS

    mock_client.get.assert_called_once_with(
        "fnlttSinglAcntAll.json",
        {
            "corp_code": "00126380",
            "bsns_year": "2025",
            "reprt_code": "11011",
            "fs_div": "CFS",
        },
    )

    mock_parse.assert_called_once_with(
        SAMPLE_API_RESPONSE
    )


@patch(
    "dart.financial_statement_service."
    "save_financial_statements"
)
@patch(
    "dart.financial_statement_service."
    "fetch_financial_statements_from_dart"
)
def test_sync_financial_statements_saves_downloaded_rows(
    mock_fetch: Mock,
    mock_save: Mock,
):
    """
    DART에서 받은 재무제표가 Repository 저장 함수에
    전달되는지 확인한다.
    """
    mock_client = Mock()

    mock_fetch.return_value = (
        PARSED_FINANCIAL_STATEMENTS
    )
    mock_save.return_value = 1

    result = sync_financial_statements(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        client=mock_client,
    )

    assert result == {
        "received_count": 1,
        "saved_count": 1,
        "ignored_count": 0,
    }

    mock_fetch.assert_called_once_with(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        client=mock_client,
    )

    mock_save.assert_called_once_with(
        PARSED_FINANCIAL_STATEMENTS
    )


@patch(
    "dart.financial_statement_service."
    "save_financial_statements"
)
@patch(
    "dart.financial_statement_service."
    "fetch_financial_statements_from_dart"
)
def test_sync_financial_statements_counts_ignored_rows(
    mock_fetch: Mock,
    mock_save: Mock,
):
    """
    이미 저장된 행이 있어 Repository가 일부만 저장한 경우,
    무시된 행 수가 정확히 계산되는지 확인한다.
    """
    statements = [
        PARSED_FINANCIAL_STATEMENTS[0],
        {
            **PARSED_FINANCIAL_STATEMENTS[0],
            "account_id": "ifrs-full_Liabilities",
            "account_nm": "부채총계",
        },
    ]

    mock_fetch.return_value = statements
    mock_save.return_value = 1

    result = sync_financial_statements(
        corp_code="00126380",
        bsns_year="2025",
    )

    assert result["received_count"] == 2
    assert result["saved_count"] == 1
    assert result["ignored_count"] == 1


@patch(
    "dart.financial_statement_service."
    "save_financial_statements"
)
@patch(
    "dart.financial_statement_service."
    "fetch_financial_statements_from_dart"
)
def test_sync_financial_statements_handles_empty_response(
    mock_fetch: Mock,
    mock_save: Mock,
):
    """
    조회된 재무제표가 없을 때에도 정상적인 결과를
    반환하는지 확인한다.
    """
    mock_fetch.return_value = []
    mock_save.return_value = 0

    result = sync_financial_statements(
        corp_code="00126380",
        bsns_year="2025",
    )

    assert result == {
        "received_count": 0,
        "saved_count": 0,
        "ignored_count": 0,
    }

    mock_save.assert_called_once_with([])