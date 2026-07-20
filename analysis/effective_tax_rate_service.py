from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)


TAX_EXPENSE_ACCOUNT_NAMES = (
    "법인세비용",
    "법인세비용(수익)",
    "법인세 비용",
)


PROFIT_BEFORE_TAX_ACCOUNT_NAMES = (
    "법인세비용차감전순이익",
    "법인세비용차감전계속사업이익",
    "법인세비용차감전이익",
    "법인세비용차감전순이익(손실)", 
    "법인세차감전순이익",
)

def calculate_company_effective_tax_rate(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> dict:
    """
    저장된 재무제표에서 법인세비용과
    법인세비용차감전순이익을 찾아 실효세율을 계산한다.
    """
    rows = fetch_financial_statements_from_db(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
        sj_div=None,
    )

    if not rows:
        raise ValueError(
            "저장된 재무제표를 찾지 못했습니다."
        )

    tax_expense = None
    profit_before_tax = None

    for row in rows:
        account_name = row.get("account_nm")
        amount = row.get("thstrm_amount")

        if account_name in TAX_EXPENSE_ACCOUNT_NAMES:
            tax_expense = amount

        elif account_name in PROFIT_BEFORE_TAX_ACCOUNT_NAMES:
            profit_before_tax = amount

    if tax_expense is None:
        raise ValueError(
            "'법인세비용' 계정을 찾지 못했습니다."
        )

    if profit_before_tax is None:
        raise ValueError(
            "'법인세비용차감전순이익' 계정을 "
            "찾지 못했습니다."
        )

    effective_tax_rate = calculate_effective_tax_rate(
        tax_expense=tax_expense,
        profit_before_tax=profit_before_tax,
    )

    return {
        "tax_expense": tax_expense,
        "profit_before_tax": profit_before_tax,
        "effective_tax_rate": effective_tax_rate,
    }



def calculate_effective_tax_rate(
    tax_expense: int | float,
    profit_before_tax: int | float,
) -> float | None:
    """
    법인세비용과 법인세비용차감전순이익을 이용해
    실효세율을 계산한다.

    실효세율 = 법인세비용
              / 법인세비용차감전순이익
              * 100

    법인세비용차감전순이익이 0 이하인 경우에는
    일반적인 세율로 해석하기 어려우므로 None을 반환한다.
    """
    if profit_before_tax <= 0:
        return None

    return (
        tax_expense
        / profit_before_tax
        * 100
    )