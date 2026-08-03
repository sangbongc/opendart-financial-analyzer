from decimal import Decimal
from unittest.mock import patch

from analysis.eps_service import get_eps_analysis


@patch("analysis.eps_service.fetch_financial_statements_from_db")
def test_get_eps_analysis_returns_basic_and_diluted_eps(mock_fetch):
    mock_fetch.return_value = [
        {
            "rcept_no": "20260310002820",
            "sj_div": "IS",
            "account_id": "ifrs-full_BasicEarningsLossPerShare",
            "account_nm": "기본주당이익",
            "thstrm_amount": "6338",
            "frmtrm_amount": "4950",
            "currency": "KRW",
        },
        {
            "rcept_no": "20260310002820",
            "sj_div": "IS",
            "account_id": "ifrs-full_DilutedEarningsLossPerShare",
            "account_nm": "희석주당이익",
            "thstrm_amount": "6305",
            "frmtrm_amount": "4920",
            "currency": "KRW",
        },
    ]

    result = get_eps_analysis("00126380", "2025")

    assert result["basic_eps"] == Decimal("6338")
    assert result["previous_basic_eps"] == Decimal("4950")
    assert result["basic_eps_change_rate"].quantize(Decimal("0.01")) == Decimal("28.04")
    assert result["diluted_eps"] == Decimal("6305")


@patch("analysis.eps_service.fetch_financial_statements_from_db")
def test_get_eps_analysis_uses_account_name_fallback(mock_fetch):
    mock_fetch.return_value = [
        {
            "rcept_no": "1",
            "sj_div": "CIS",
            "account_id": "custom_EarningsPerShare",
            "account_nm": "기본주당순이익(원)",
            "thstrm_amount": "1200",
            "frmtrm_amount": "1000",
        }
    ]

    result = get_eps_analysis("00000000", "2025")

    assert result["basic_eps"] == Decimal("1200")
    assert result["basic_eps_change_rate"] == Decimal("20.0")


@patch("analysis.eps_service.fetch_financial_statements_from_db")
def test_get_eps_analysis_returns_empty_result(mock_fetch):
    mock_fetch.return_value = []

    result = get_eps_analysis("00000000", "2025")

    assert result["basic_eps"] is None
    assert result["source_rows"] == []
