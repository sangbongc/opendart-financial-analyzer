from decimal import Decimal
from unittest.mock import Mock, patch

from analysis.account_change_ratio_service import (
    AccountChangeRatioError,
    calculate_account_change_ratio,
    calculate_account_change_ratios,
    get_account_change_ratios,
)


def test_calculate_account_change_ratio_increase() -> None:
    result = calculate_account_change_ratio(
        current_amount="1,200",
        previous_amount="1,000",
    )

    assert result["change_amount"] == Decimal("200")
    assert result["change_ratio"] == Decimal("20.0")


def test_calculate_account_change_ratio_decrease() -> None:
    result = calculate_account_change_ratio(
        current_amount="800",
        previous_amount="1,000",
    )

    assert result["change_amount"] == Decimal("-200")
    assert result["change_ratio"] == Decimal("-20.0")


def test_calculate_account_change_ratio_previous_zero() -> None:
    result = calculate_account_change_ratio(
        current_amount="1,000",
        previous_amount="0",
    )

    assert result["change_amount"] == Decimal("1000")
    assert result["change_ratio"] is None


def test_calculate_account_change_ratio_missing_amount() -> None:
    result = calculate_account_change_ratio(
        current_amount=None,
        previous_amount="1,000",
    )

    assert result["change_amount"] is None
    assert result["change_ratio"] is None


def test_calculate_account_change_ratio_negative_to_positive() -> None:
    result = calculate_account_change_ratio(
        current_amount="50",
        previous_amount="-100",
    )

    assert result["change_amount"] == Decimal("150")
    assert result["change_ratio"] == Decimal("150.0")


def test_calculate_account_change_ratios() -> None:
    financial_statements = [
        {
            "corp_code": "00126380",
            "bsns_year": "2025",
            "reprt_code": "11011",
            "fs_div": "CFS",
            "fs_nm": "연결재무제표",
            "sj_div": "BS",
            "sj_nm": "재무상태표",
            "account_id": "ifrs-full_Inventories",
            "account_nm": "재고자산",
            "account_detail": None,
            "thstrm_nm": "제57기",
            "frmtrm_nm": "제56기",
            "thstrm_amount": "1,200",
            "frmtrm_amount": "1,000",
        }
    ]

    results = calculate_account_change_ratios(
        financial_statements
    )

    assert len(results) == 1

    result = results[0]

    assert result["account_nm"] == "재고자산"
    assert result["current_amount"] == Decimal("1200")
    assert result["previous_amount"] == Decimal("1000")
    assert result["change_amount"] == Decimal("200")
    assert result["change_ratio"] == Decimal("20.0")


@patch(
    "analysis.account_change_ratio_service."
    "fetch_financial_statements_from_db"
)
def test_get_account_change_ratios(
    mock_fetch_financial_statements_from_db: Mock,
) -> None:
    mock_fetch_financial_statements_from_db.return_value = [
        {
            "corp_code": "00126380",
            "bsns_year": "2025",
            "reprt_code": "11011",
            "fs_div": "CFS",
            "fs_nm": "연결재무제표",
            "sj_div": "BS",
            "sj_nm": "재무상태표",
            "account_id": "ifrs-full_Inventories",
            "account_nm": "재고자산",
            "account_detail": None,
            "thstrm_nm": "제57기",
            "frmtrm_nm": "제56기",
            "thstrm_amount": "1,200",
            "frmtrm_amount": "1,000",
        }
    ]

    results = get_account_change_ratios(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        sj_div="BS",
    )

    mock_fetch_financial_statements_from_db.assert_called_once_with(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        sj_div="BS",
    )

    assert len(results) == 1
    assert results[0]["change_ratio"] == Decimal("20.0")


@patch(
    "analysis.account_change_ratio_service."
    "fetch_financial_statements_from_db"
)
def test_get_account_change_ratios_empty(
    mock_fetch_financial_statements_from_db: Mock,
) -> None:
    mock_fetch_financial_statements_from_db.return_value = []

    results = get_account_change_ratios(
        corp_code="00126380",
        bsns_year="2025",
    )

    assert results == []


@patch(
    "analysis.account_change_ratio_service."
    "fetch_financial_statements_from_db"
)
def test_get_account_change_ratios_repository_error(
    mock_fetch_financial_statements_from_db: Mock,
) -> None:
    mock_fetch_financial_statements_from_db.side_effect = RuntimeError(
        "database error"
    )

    try:
        get_account_change_ratios(
            corp_code="00126380",
            bsns_year="2025",
        )

    except AccountChangeRatioError as error:
        assert (
            str(error)
            == "재무제표 조회 중 오류가 발생했습니다."
        )

    else:
        raise AssertionError(
            "AccountChangeRatioError가 발생해야 합니다."
        )