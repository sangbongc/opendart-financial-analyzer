from unittest.mock import Mock
from unittest.mock import patch

from dart.financial_statement_service import (
    fetch_financial_statements,
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

    result = fetch_financial_statements(
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