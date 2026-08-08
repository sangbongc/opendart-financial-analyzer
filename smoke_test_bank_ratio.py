from __future__ import annotations

from typing import Any

from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)
from analysis.finance_company_analysis.bank_account_selector import (
    find_bank_account_row,
)
from analysis.finance_company_analysis.bank_ratio_service import (
    BankRatioCalculationError,
    calculate_bank_ratios,
)


BS_ACCOUNT_KEYS = (
    "total_assets",
    "total_liabilities",
    "total_equity",
    "cash_and_deposits",
    "loans",
    "fvpl_assets",
    "fvoci_assets",
    "amortized_cost_securities",
    "derivative_assets",
    "deposits",
    "borrowings",
    "bonds",
    "fvpl_liabilities",
    "derivative_liabilities",
)

IS_ACCOUNT_KEYS = (
    "net_interest_income",
    "net_fee_income",
    "credit_loss",
    "net_income",
    "operating_profit",
)


def _format_amount(value: Any) -> str:
    if value is None:
        return "-"

    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _format_ratio(value: Any) -> str:
    if value is None:
        return "-"

    try:
        return f"{float(value):.4f}%"
    except (TypeError, ValueError):
        return str(value)


def _print_selected_accounts(
    statements: list[dict[str, Any]],
) -> None:
    print()
    print("[2. 은행 주요 계정 selector]")
    print("-" * 110)
    print(
        f"{'KEY':32}"
        f"{'재무제표':10}"
        f"{'선택 계정명':32}"
        f"{'당기':18}"
        f"{'전기':18}"
    )
    print("-" * 110)

    for account_key in BS_ACCOUNT_KEYS:
        row = find_bank_account_row(
            statements,
            account_key=account_key,
            statement_divisions=("BS",),
        )
        _print_account_row(account_key, row)

    for account_key in IS_ACCOUNT_KEYS:
        row = find_bank_account_row(
            statements,
            account_key=account_key,
            statement_divisions=("IS", "CIS"),
        )
        _print_account_row(account_key, row)


def _print_account_row(
    account_key: str,
    row: dict[str, Any] | None,
) -> None:
    if row is None:
        print(
            f"{account_key:32}"
            f"{'-':10}"
            f"{'NOT FOUND':32}"
            f"{'-':18}"
            f"{'-':18}"
        )
        return

    print(
        f"{account_key:32}"
        f"{str(row.get('sj_div') or '-'):10}"
        f"{str(row.get('account_nm') or '-'):32}"
        f"{_format_amount(row.get('thstrm_amount')):18}"
        f"{_format_amount(row.get('frmtrm_amount')):18}"
    )


def run_smoke_test(
    *,
    corp_code: str,
    corp_name: str = "",
    bsns_year: str = "2025",
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> None:
    """
    실제 SQLite DB에 저장된 재무제표를 이용해
    은행 계정 selector와 은행 재무비율 계산을 검증한다.

    DB에는 비율 계산 결과를 저장하지 않는다.
    """
    print()
    print("=" * 110)
    print("[은행 재무비율 Smoke Test]")
    print("=" * 110)

    if corp_name:
        print(f"기업명: {corp_name}")

    print(f"고유번호: {corp_code}")
    print(f"사업연도: {bsns_year}")
    print(f"보고서 코드: {reprt_code}")
    print(f"재무제표 구분: {fs_div}")

    statements = fetch_financial_statements_from_db(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
    )

    print()
    print("[1. 원본 재무제표 조회]")
    print("-" * 60)
    print(f"조회 행 수: {len(statements)}")

    if not statements:
        print("조건에 해당하는 재무제표가 DB에 없습니다.")
        return

    _print_selected_accounts(statements)

    print()
    print("[3. 은행 재무비율 계산]")
    print("-" * 80)

    try:
        ratios = calculate_bank_ratios(
            statements=statements,
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )
    except BankRatioCalculationError as error:
        print(f"계산 실패: {error}")
        return

    unavailable = []

    for ratio in ratios:
        value = ratio.get("ratio_value")

        if value is None:
            unavailable.append(ratio["ratio_code"])

        print(
            f"{ratio['ratio_code']:36}"
            f"{ratio['ratio_name']:28}"
            f"{_format_ratio(value)}"
        )

    print()
    print("[4. 결과 요약]")
    print("-" * 60)
    print(f"계산 대상 비율: {len(ratios)}")
    print(
        "계산 성공: "
        f"{sum(1 for row in ratios if row.get('ratio_value') is not None)}"
    )
    print(f"계산 불가: {len(unavailable)}")

    if unavailable:
        print("계산 불가 비율:")
        for ratio_code in unavailable:
            print(f"  - {ratio_code}")
    else:
        print("모든 은행 재무비율이 계산되었습니다.")


BANKS = (
    ("KB금융", "00688996"),
    ("신한지주", "00382199"),
    ("하나금융지주", "00547583"),
    ("우리금융지주", "01350869"),
    ("농협금융지주", "00908021"),
)


def main():
    for corp_name, corp_code in BANKS:
        run_smoke_test(
            corp_code=corp_code,
            corp_name=corp_name,
            bsns_year="2025",
            reprt_code="11011",
            fs_div="CFS",
        )

if __name__ == "__main__":
    main()