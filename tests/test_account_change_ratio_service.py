from decimal import Decimal
from unittest.mock import Mock, patch

from analysis.account_change_ratio_service import (
    AccountChangeRatioError,
    calculate_account_change_ratio,
    calculate_account_change_ratios,
    get_account_change_ratios,
    get_major_account_change_ratios,
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
    

@patch(
    "analysis.account_change_ratio_service.get_account_change_ratios"
)
def test_get_major_account_change_ratios_filters_accounts(
    mock_get_change_ratios,
):
    mock_get_change_ratios.return_value = [
        {
            "account_nm": "매출액",
            "change_ratio": 10,
        },
        {
            "account_nm": "재고자산",
            "change_ratio": 20,
        },
        {
            "account_nm": "유형자산",
            "change_ratio": 30,
        },
    ]

    result = get_major_account_change_ratios(
        corp_code="00126380",
        bsns_year="2025",
        major_accounts_by_statement={
    "IS": [
        "매출액",
    ],
    "BS": [
        "유형자산",
    ],
},
    )

    assert len(result) == 2
    assert result[0]["account_nm"] == "매출액"
    assert result[1]["account_nm"] == "유형자산"


@patch(
    "analysis.account_change_ratio_service.get_account_change_ratios"
)
def test_get_major_account_change_ratios_preserves_order(
    mock_get_change_ratios,
):
    mock_get_change_ratios.return_value = [
        {
            "account_nm": "유형자산",
            "change_ratio": 30,
        },
        {
            "account_nm": "매출액",
            "change_ratio": 10,
        },
    ]

    result = get_major_account_change_ratios(
        corp_code="00126380",
        bsns_year="2025",
        major_accounts_by_statement={
    "IS": [
        "매출액",
    ],
    "BS": [
        "유형자산",
    ],
},
    )

    assert [row["account_nm"] for row in result] == [
        "매출액",
        "유형자산",
    ]


@patch(
    "analysis.account_change_ratio_service.get_account_change_ratios"
)
def test_get_major_account_change_ratios_ignores_unknown_accounts(
    mock_get_change_ratios,
):
    mock_get_change_ratios.return_value = [
        {
            "account_nm": "유형자산",
            "change_ratio": 30,
        },
    ]

    result = get_major_account_change_ratios(
        corp_code="00126380",
        bsns_year="2025",
        major_accounts_by_statement={"IS":
            "매출액",
        },
    )

    assert result == []


@patch(
    "analysis.account_change_ratio_service.get_account_change_ratios"
)
def test_get_major_account_change_ratios_normalizes_account_names(
    mock_get_change_ratios,
):
    mock_get_change_ratios.return_value = [
        {
            "account_nm": "매 출 액",
            "change_ratio": 10,
        },
    ]

    result = get_major_account_change_ratios(
        corp_code="00126380",
        bsns_year="2025",
        major_accounts_by_statement={
            "IS": [
                "매출액",
            ],
        },
    )

    assert len(result) == 1
    assert result[0]["account_nm"] == "매 출 액"
    assert result[0]["sj_div"] == "IS"


@patch(
    "analysis.account_change_ratio_service.get_account_change_ratios"
)
def test_get_major_account_change_ratios_returns_empty_for_empty_major_accounts(
    mock_get_change_ratios,
):
    result = get_major_account_change_ratios(
        corp_code="00126380",
        bsns_year="2025",
        major_accounts_by_statement={},
    )

    assert result == []
    mock_get_change_ratios.assert_not_called()