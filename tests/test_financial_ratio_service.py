from unittest.mock import Mock, patch

import pytest

from analysis.financial_ratio_service import (
    FinancialRatioCalculationError,
    calculate_and_save_financial_ratios,
    calculate_financial_ratios,
)


CORP_CODE = "00126380"
BSNS_YEAR = "2025"
REPRT_CODE = "11011"
FS_DIV = "CFS"
CALCULATION_VERSION = "v2_average_balance"


@pytest.fixture
def financial_statements() -> list[dict]:
    """
    재무비율 계산에 필요한 기본 재무제표 데이터를 반환한다.

    예상 계산 결과
    ----------------
    영업이익률:
        100 / 1,000 × 100 = 10%

    순이익률:
        80 / 1,000 × 100 = 8%

    평균자산:
        (1,200 + 1,000) / 2 = 1,100

    ROA:
        80 / 1,100 × 100 = 약 7.2727%

    평균자본:
        (800 + 700) / 2 = 750

    ROE:
        80 / 750 × 100 = 약 10.6667%

    부채비율:
        400 / 800 × 100 = 50%

    유동비율:
        500 / 200 × 100 = 250%
    """
    return [
        {
            "sj_div": "BS",
            "account_id": "ifrs-full_Assets",
            "account_nm": "자산총계",
            "account_detail": "",
            "thstrm_amount": "1,200",
            "frmtrm_amount": "1,000",
        },
        {
            "sj_div": "BS",
            "account_id": "ifrs-full_Equity",
            "account_nm": "자본총계",
            "account_detail": "",
            "thstrm_amount": "800",
            "frmtrm_amount": "700",
        },
        {
            "sj_div": "BS",
            "account_id": "ifrs-full_Liabilities",
            "account_nm": "부채총계",
            "account_detail": "",
            "thstrm_amount": "400",
            "frmtrm_amount": "300",
        },
        {
            "sj_div": "BS",
            "account_id": "ifrs-full_CurrentAssets",
            "account_nm": "유동자산",
            "account_detail": "",
            "thstrm_amount": "500",
            "frmtrm_amount": "450",
        },
        {
            "sj_div": "BS",
            "account_id": "ifrs-full_CurrentLiabilities",
            "account_nm": "유동부채",
            "account_detail": "",
            "thstrm_amount": "200",
            "frmtrm_amount": "180",
        },
        {
            "sj_div": "IS",
            "account_id": "ifrs-full_Revenue",
            "account_nm": "매출액",
            "account_detail": "",
            "thstrm_amount": "1,000",
            "frmtrm_amount": "900",
        },
        {
            "sj_div": "IS",
            "account_id": "dart_OperatingIncomeLoss",
            "account_nm": "영업이익",
            "account_detail": "",
            "thstrm_amount": "100",
            "frmtrm_amount": "90",
        },
        {
            "sj_div": "IS",
            "account_id": "ifrs-full_ProfitLoss",
            "account_nm": "당기순이익",
            "account_detail": "",
            "thstrm_amount": "80",
            "frmtrm_amount": "70",
        },
    ]


def _to_ratio_dict(
    ratios: list[dict],
) -> dict[str, dict]:
    """
    재무비율 결과를 ratio_code를 키로 하는 딕셔너리로 변환한다.
    """
    return {
        ratio["ratio_code"]: ratio
        for ratio in ratios
    }


def test_calculate_financial_ratios_returns_all_ratios(
    financial_statements: list[dict],
) -> None:
    """
    재무제표를 전달하면 주요 재무비율 6개가 모두 반환되는지 확인한다.
    """
    ratios = calculate_financial_ratios(
        statements=financial_statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    assert len(ratios) == 6

    ratio_codes = {
        ratio["ratio_code"]
        for ratio in ratios
    }

    assert ratio_codes == {
        "OPERATING_MARGIN",
        "NET_PROFIT_MARGIN",
        "ROA",
        "ROE",
        "DEBT_RATIO",
        "CURRENT_RATIO",
    }

    for ratio in ratios:
        assert ratio["corp_code"] == CORP_CODE
        assert ratio["bsns_year"] == BSNS_YEAR
        assert ratio["reprt_code"] == REPRT_CODE
        assert ratio["fs_div"] == FS_DIV
        assert (
            ratio["calculation_version"]
            == CALCULATION_VERSION
        )


def test_calculate_financial_ratios_calculates_correct_values(
    financial_statements: list[dict],
) -> None:
    """
    각 재무비율의 계산 결과가 예상값과 일치하는지 확인한다.
    """
    ratios = calculate_financial_ratios(
        statements=financial_statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    assert ratio_dict["OPERATING_MARGIN"][
        "ratio_value"
    ] == pytest.approx(10.0)

    assert ratio_dict["NET_PROFIT_MARGIN"][
        "ratio_value"
    ] == pytest.approx(8.0)

    assert ratio_dict["ROA"][
        "ratio_value"
    ] == pytest.approx(
        7.272727,
        rel=1e-5,
    )

    assert ratio_dict["ROE"][
        "ratio_value"
    ] == pytest.approx(
        10.666667,
        rel=1e-5,
    )

    assert ratio_dict["DEBT_RATIO"][
        "ratio_value"
    ] == pytest.approx(50.0)

    assert ratio_dict["CURRENT_RATIO"][
        "ratio_value"
    ] == pytest.approx(250.0)


def test_calculate_financial_ratios_uses_average_assets_and_equity(
    financial_statements: list[dict],
) -> None:
    """
    ROA와 ROE의 분모가 당기말 잔액이 아니라
    당기말·전기말 평균잔액인지 확인한다.
    """
    ratios = calculate_financial_ratios(
        statements=financial_statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    roa = ratio_dict["ROA"]
    roe = ratio_dict["ROE"]

    assert roa["numerator_value"] == 80
    assert roa["denominator_value"] == 1_100

    assert roe["numerator_value"] == 80
    assert roe["denominator_value"] == 750


def test_calculate_financial_ratios_returns_none_when_previous_amount_missing(
    financial_statements: list[dict],
) -> None:
    """
    자산총계와 자본총계의 전기 금액이 없으면
    평균잔액을 계산할 수 없으므로 ROA와 ROE가 None인지 확인한다.

    다른 비율은 당기 금액만으로 정상 계산되어야 한다.
    """
    statements = [
        row.copy()
        for row in financial_statements
    ]

    for row in statements:
        if row["account_nm"] in {
            "자산총계",
            "자본총계",
        }:
            row["frmtrm_amount"] = None

    ratios = calculate_financial_ratios(
        statements=statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    assert ratio_dict["ROA"]["ratio_value"] is None
    assert ratio_dict["ROA"]["denominator_value"] is None

    assert ratio_dict["ROE"]["ratio_value"] is None
    assert ratio_dict["ROE"]["denominator_value"] is None

    assert ratio_dict["OPERATING_MARGIN"][
        "ratio_value"
    ] == pytest.approx(10.0)

    assert ratio_dict["NET_PROFIT_MARGIN"][
        "ratio_value"
    ] == pytest.approx(8.0)

    assert ratio_dict["DEBT_RATIO"][
        "ratio_value"
    ] == pytest.approx(50.0)

    assert ratio_dict["CURRENT_RATIO"][
        "ratio_value"
    ] == pytest.approx(250.0)


def test_calculate_financial_ratios_handles_zero_denominator(
    financial_statements: list[dict],
) -> None:
    """
    비율의 분모가 0이면 ZeroDivisionError 없이
    ratio_value가 None으로 반환되는지 확인한다.
    """
    statements = [
        row.copy()
        for row in financial_statements
    ]

    for row in statements:
        if row["account_nm"] == "유동부채":
            row["thstrm_amount"] = "0"

    ratios = calculate_financial_ratios(
        statements=statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    current_ratio = ratio_dict["CURRENT_RATIO"]

    assert current_ratio["numerator_value"] == 500
    assert current_ratio["denominator_value"] == 0
    assert current_ratio["ratio_value"] is None


def test_calculate_financial_ratios_handles_missing_account(
    financial_statements: list[dict],
) -> None:
    """
    매출액 계정이 없으면 매출액을 분모로 사용하는
    영업이익률과 순이익률이 None인지 확인한다.
    """
    statements = [
        row.copy()
        for row in financial_statements
        if row["account_nm"] != "매출액"
    ]

    ratios = calculate_financial_ratios(
        statements=statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    assert ratio_dict["OPERATING_MARGIN"][
        "ratio_value"
    ] is None

    assert ratio_dict["OPERATING_MARGIN"][
        "denominator_value"
    ] is None

    assert ratio_dict["NET_PROFIT_MARGIN"][
        "ratio_value"
    ] is None

    assert ratio_dict["NET_PROFIT_MARGIN"][
        "denominator_value"
    ] is None

    assert ratio_dict["ROA"][
        "ratio_value"
    ] == pytest.approx(
        7.272727,
        rel=1e-5,
    )


def test_calculate_financial_ratios_supports_account_aliases(
    financial_statements: list[dict],
) -> None:
    """
    매출액 대신 영업수익이라는 계정명이 사용되어도
    매출액 계정으로 인식하는지 확인한다.
    """
    statements = [
        row.copy()
        for row in financial_statements
    ]

    for row in statements:
        if row["account_nm"] == "매출액":
            row["account_nm"] = "영업수익"

    ratios = calculate_financial_ratios(
        statements=statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    assert ratio_dict["OPERATING_MARGIN"][
        "ratio_value"
    ] == pytest.approx(10.0)

    assert ratio_dict["NET_PROFIT_MARGIN"][
        "ratio_value"
    ] == pytest.approx(8.0)


def test_calculate_financial_ratios_normalizes_account_name_spaces(
    financial_statements: list[dict],
) -> None:
    """
    계정명에 불필요한 공백이 포함되어도
    정상적으로 계정을 찾는지 확인한다.
    """
    statements = [
        row.copy()
        for row in financial_statements
    ]

    for row in statements:
        if row["account_nm"] == "영업이익":
            row["account_nm"] = "영업 이익"

    ratios = calculate_financial_ratios(
        statements=statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    assert ratio_dict["OPERATING_MARGIN"][
        "ratio_value"
    ] == pytest.approx(10.0)


def test_calculate_financial_ratios_parses_parenthesized_negative_amount(
    financial_statements: list[dict],
) -> None:
    """
    괄호로 표시된 음수 금액을 정상적으로 해석하는지 확인한다.
    """
    statements = [
        row.copy()
        for row in financial_statements
    ]

    for row in statements:
        if row["account_nm"] == "영업이익":
            row["thstrm_amount"] = "(100)"

    ratios = calculate_financial_ratios(
        statements=statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    operating_margin = ratio_dict[
        "OPERATING_MARGIN"
    ]

    assert operating_margin["numerator_value"] == -100

    assert operating_margin[
        "ratio_value"
    ] == pytest.approx(-10.0)


def test_calculate_financial_ratios_prefers_default_account_row(
    financial_statements: list[dict],
) -> None:
    """
    동일한 계정명이 여러 행에 존재하면 account_detail이 없는
    기본 계정 행을 우선하는지 확인한다.
    """
    statements = [
        {
            "sj_div": "IS",
            "account_id": "custom_RevenueSegment",
            "account_nm": "매출액",
            "account_detail": "특정 사업부문",
            "thstrm_amount": "300",
            "frmtrm_amount": "250",
        },
        *[
            row.copy()
            for row in financial_statements
        ],
    ]

    ratios = calculate_financial_ratios(
        statements=statements,
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    ratio_dict = _to_ratio_dict(ratios)

    # 세부 매출액 300이 아니라 기본 매출액 1,000을 사용해야 한다.
    assert ratio_dict["OPERATING_MARGIN"][
        "denominator_value"
    ] == 1_000

    assert ratio_dict["OPERATING_MARGIN"][
        "ratio_value"
    ] == pytest.approx(10.0)


def test_calculate_financial_ratios_raises_when_statements_empty() -> None:
    """
    빈 재무제표를 전달하면 계산 예외가 발생하는지 확인한다.
    """
    with pytest.raises(
        FinancialRatioCalculationError,
        match="재무비율 계산에 사용할 재무제표가 없습니다",
    ):
        calculate_financial_ratios(
            statements=[],
            corp_code=CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE,
            fs_div=FS_DIV,
            calculation_version=CALCULATION_VERSION,
        )


@patch(
    "analysis.financial_ratio_service.upsert_financial_ratios"
)
@patch(
    "analysis.financial_ratio_service.fetch_financial_statements_from_db"
)
def test_calculate_and_save_financial_ratios(
    mock_fetch_financial_statements_from_db: Mock,
    mock_upsert_financial_ratios: Mock,
    financial_statements: list[dict],
) -> None:
    """
    저장된 재무제표를 조회하고 계산 결과를 Repository에
    전달한 뒤 결과 요약을 반환하는지 확인한다.
    """
    mock_fetch_financial_statements_from_db.return_value = (
        financial_statements
    )
    mock_upsert_financial_ratios.return_value = 6

    result = calculate_and_save_financial_ratios(
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    mock_fetch_financial_statements_from_db.assert_called_once_with(
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
    )

    mock_upsert_financial_ratios.assert_called_once()

    saved_ratios = (
        mock_upsert_financial_ratios.call_args.args[0]
    )

    assert len(saved_ratios) == 6

    assert result["corp_code"] == CORP_CODE
    assert result["bsns_year"] == BSNS_YEAR
    assert result["reprt_code"] == REPRT_CODE
    assert result["fs_div"] == FS_DIV

    assert (
        result["calculation_version"]
        == CALCULATION_VERSION
    )

    assert result["calculated_count"] == 6
    assert result["saved_count"] == 6
    assert result["unavailable_ratios"] == []
    assert len(result["ratios"]) == 6


@patch(
    "analysis.financial_ratio_service.upsert_financial_ratios"
)
@patch(
    "analysis.financial_ratio_service.fetch_financial_statements_from_db"
)
def test_calculate_and_save_reports_unavailable_ratios(
    mock_fetch_financial_statements_from_db: Mock,
    mock_upsert_financial_ratios: Mock,
    financial_statements: list[dict],
) -> None:
    """
    전기 자산·자본 금액이 없어 ROA와 ROE를 계산하지 못하면
    unavailable_ratios에 해당 코드가 포함되는지 확인한다.
    """
    statements = [
        row.copy()
        for row in financial_statements
    ]

    for row in statements:
        if row["account_nm"] in {
            "자산총계",
            "자본총계",
        }:
            row["frmtrm_amount"] = None

    mock_fetch_financial_statements_from_db.return_value = statements
    mock_upsert_financial_ratios.return_value = 6

    result = calculate_and_save_financial_ratios(
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
        calculation_version=CALCULATION_VERSION,
    )

    assert set(result["unavailable_ratios"]) == {
        "ROA",
        "ROE",
    }

    mock_upsert_financial_ratios.assert_called_once()


@patch(
    "analysis.financial_ratio_service.upsert_financial_ratios"
)
@patch(
    "analysis.financial_ratio_service.fetch_financial_statements_from_db"
)
def test_calculate_and_save_raises_when_statement_not_found(
    mock_fetch_financial_statements_from_db: Mock,
    mock_upsert_financial_ratios: Mock,
) -> None:
    """
    저장된 재무제표가 없으면 예외를 발생시키고
    재무비율 저장 Repository를 호출하지 않는지 확인한다.
    """
    mock_fetch_financial_statements_from_db.return_value = []

    with pytest.raises(
        FinancialRatioCalculationError,
        match="조건에 해당하는 재무제표가 저장되어 있지 않습니다",
    ):
        calculate_and_save_financial_ratios(
            corp_code=CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE,
            fs_div=FS_DIV,
            calculation_version=CALCULATION_VERSION,
        )

    mock_upsert_financial_ratios.assert_not_called()