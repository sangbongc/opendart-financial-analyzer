from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any

from database.financial_ratio_repository import (
    upsert_financial_ratios,
)
from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)
from analysis.finance_company_analysis.bank_account_selector import (
    find_bank_account_row,
)


class BankRatioCalculationError(Exception):
    """
    은행·금융지주 재무비율 계산에 필요한 계정을 찾지 못했거나
    금액을 해석할 수 없는 경우 발생한다.
    """


CALCULATION_VERSION = "bank_v1_average_balance"


def calculate_bank_ratios(
    statements: Iterable[dict[str, Any]],
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    calculation_version: str = CALCULATION_VERSION,
) -> list[dict]:
    """
    은행·금융지주 연결재무제표를 기반으로 금융업용 비율을 계산한다.

    1차 계산 지표
    -------------
    - ROA
    - ROE
    - 순이자손익 / 평균자산
    - 순수수료손익 / 평균자산
    - 대출채권(등) / 총자산
    - 예수부채 / 총부채
    - 차입부채 / 총부채
    - 신용손실비용 / 평균대출채권(등)

    주의
    ----
    이 지표들은 OpenDART 재무제표 계정을 이용한 비교 지표이다.
    NIM, BIS 자기자본비율, 고정이하여신비율 등 감독 목적의
    공식 은행 건전성 지표를 대체하지 않는다.
    """
    statement_rows = list(statements)

    if not statement_rows:
        raise BankRatioCalculationError(
            "은행 재무비율 계산에 사용할 재무제표가 없습니다."
        )

    net_income, _ = _extract_account_amounts(
        statement_rows,
        account_key="net_income",
        statement_divisions=("IS", "CIS"),
    )
    net_interest_income, _ = _extract_account_amounts(
        statement_rows,
        account_key="net_interest_income",
        statement_divisions=("IS", "CIS"),
    )
    net_fee_income, _ = _extract_account_amounts(
        statement_rows,
        account_key="net_fee_income",
        statement_divisions=("IS", "CIS"),
    )
    credit_loss, _ = _extract_account_amounts(
        statement_rows,
        account_key="credit_loss",
        statement_divisions=("IS", "CIS"),
    )

    current_assets, previous_assets = _extract_account_amounts(
        statement_rows,
        account_key="total_assets",
        statement_divisions=("BS",),
    )
    current_equity, previous_equity = _extract_account_amounts(
        statement_rows,
        account_key="total_equity",
        statement_divisions=("BS",),
    )
    total_liabilities, _ = _extract_account_amounts(
        statement_rows,
        account_key="total_liabilities",
        statement_divisions=("BS",),
    )
    current_loans, previous_loans = _extract_account_amounts(
        statement_rows,
        account_key="loans",
        statement_divisions=("BS",),
    )
    deposits, _ = _extract_account_amounts(
        statement_rows,
        account_key="deposits",
        statement_divisions=("BS",),
    )
    borrowings, _ = _extract_account_amounts(
        statement_rows,
        account_key="borrowings",
        statement_divisions=("BS",),
    )

    average_assets = _calculate_average(
        current_assets,
        previous_assets,
    )
    average_equity = _calculate_average(
        current_equity,
        previous_equity,
    )
    average_loans = _calculate_average(
        current_loans,
        previous_loans,
    )

    ratio_specs = (
        (
            "BANK_ROA",
            "총자산이익률(은행)",
            net_income,
            average_assets,
        ),
        (
            "BANK_ROE",
            "자기자본이익률(은행)",
            net_income,
            average_equity,
        ),
        (
            "BANK_NET_INTEREST_ASSET_RATIO",
            "순이자손익/평균자산",
            net_interest_income,
            average_assets,
        ),
        (
            "BANK_NET_FEE_ASSET_RATIO",
            "순수수료손익/평균자산",
            net_fee_income,
            average_assets,
        ),
        (
            "BANK_LOAN_ASSET_RATIO",
            "대출채권(등) 비중",
            current_loans,
            current_assets,
        ),
        (
            "BANK_DEPOSIT_LIABILITY_RATIO",
            "예수부채 비중",
            deposits,
            total_liabilities,
        ),
        (
            "BANK_BORROWING_LIABILITY_RATIO",
            "차입부채 비중",
            borrowings,
            total_liabilities,
        ),
        (
            "BANK_CREDIT_COST_RATIO",
            "신용손실비용/평균대출채권(등)",
            credit_loss,
            average_loans,
        ),
    )

    return [
        _build_ratio_result(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
            ratio_code=ratio_code,
            ratio_name=ratio_name,
            numerator=numerator,
            denominator=denominator,
            calculation_version=calculation_version,
        )
        for (
            ratio_code,
            ratio_name,
            numerator,
            denominator,
        ) in ratio_specs
    ]


def calculate_and_save_bank_ratios(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
    calculation_version: str = CALCULATION_VERSION,
) -> dict:
    """
    DB에 저장된 금융회사 재무제표를 조회해 은행 비율을 계산하고 저장한다.

    기존 financial_ratio_results 테이블과
    upsert_financial_ratios()를 그대로 사용한다.
    """
    statements = fetch_financial_statements_from_db(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
    )

    if not statements:
        raise BankRatioCalculationError(
            "조건에 해당하는 은행 재무제표가 저장되어 있지 않습니다. "
            f"corp_code={corp_code}, "
            f"bsns_year={bsns_year}, "
            f"reprt_code={reprt_code}, "
            f"fs_div={fs_div}"
        )

    ratios = calculate_bank_ratios(
        statements=statements,
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
        calculation_version=calculation_version,
    )

    saved_count = upsert_financial_ratios(ratios)

    unavailable_ratios = [
        ratio["ratio_code"]
        for ratio in ratios
        if ratio["ratio_value"] is None
    ]

    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "calculation_version": calculation_version,
        "calculated_count": len(ratios),
        "saved_count": saved_count,
        "unavailable_ratios": unavailable_ratios,
        "ratios": ratios,
    }


def _extract_account_amounts(
    statements: list[dict[str, Any]],
    *,
    account_key: str,
    statement_divisions: tuple[str, ...],
) -> tuple[Decimal | None, Decimal | None]:
    row = find_bank_account_row(
        statements,
        account_key=account_key,
        statement_divisions=statement_divisions,
    )

    if row is None:
        return None, None

    return (
        _parse_amount(row.get("thstrm_amount")),
        _parse_amount(row.get("frmtrm_amount")),
    )


def _parse_amount(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, int | float):
        return Decimal(str(value))

    text = str(value).strip()

    if not text or text == "-":
        return None

    text = text.replace(",", "")

    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"

    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise BankRatioCalculationError(
            f"금액을 숫자로 변환할 수 없습니다: {value}"
        ) from error


def _calculate_average(
    current_value: Decimal | None,
    previous_value: Decimal | None,
) -> Decimal | None:
    if current_value is None or previous_value is None:
        return None

    return (
        current_value + previous_value
    ) / Decimal("2")


def _calculate_percentage(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> float | None:
    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    return float(
        numerator / denominator * Decimal("100")
    )


def _to_storage_number(
    value: Decimal | None,
) -> int | float | None:
    if value is None:
        return None

    if value == value.to_integral_value():
        return int(value)

    return float(value)


def _build_ratio_result(
    *,
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    ratio_code: str,
    ratio_name: str,
    numerator: Decimal | None,
    denominator: Decimal | None,
    calculation_version: str,
) -> dict:
    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "ratio_code": ratio_code,
        "ratio_name": ratio_name,
        "ratio_value": _calculate_percentage(
            numerator,
            denominator,
        ),
        "numerator_value": _to_storage_number(
            numerator
        ),
        "denominator_value": _to_storage_number(
            denominator
        ),
        "calculation_version": calculation_version,
    }