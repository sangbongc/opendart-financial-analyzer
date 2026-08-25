from analysis.debt_account_selector import (
    select_interest_bearing_debt_accounts,
)
from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)


class CapitalStructureAnalysisError(Exception):
    """자본구조 분석에 실패했을 때 발생한다."""


LIABILITIES_ACCOUNT_IDS = {
    "ifrs-full_Liabilities",
}

EQUITY_ACCOUNT_IDS = {
    "ifrs-full_Equity",
}


def get_capital_structure(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> dict:
    rows = fetch_financial_statements_from_db(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
        sj_div="BS",
    )

    if not rows:
        raise CapitalStructureAnalysisError(
            "재무상태표 데이터가 없습니다."
        )

    liabilities_row = _find_account(
        rows=rows,
        account_ids=LIABILITIES_ACCOUNT_IDS,
        account_names={"부채총계"},
    )

    equity_row = _find_account(
        rows=rows,
        account_ids=EQUITY_ACCOUNT_IDS,
        account_names={"자본총계"},
    )

    if liabilities_row is None:
        raise CapitalStructureAnalysisError(
            "부채총계 계정을 찾지 못했습니다."
        )

    if equity_row is None:
        raise CapitalStructureAnalysisError(
            "자본총계 계정을 찾지 못했습니다."
        )

    liabilities = liabilities_row.get(
        "thstrm_amount"
    )
    equity = equity_row.get(
        "thstrm_amount"
    )

    if liabilities is None:
        raise CapitalStructureAnalysisError(
            "부채총계 금액이 없습니다."
        )

    if equity is None:
        raise CapitalStructureAnalysisError(
            "자본총계 금액이 없습니다."
        )

    if equity <= 0:
        raise CapitalStructureAnalysisError(
            "자본총계가 0 이하이므로 "
            "D/E를 계산할 수 없습니다."
        )

    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "rcept_no": liabilities_row["rcept_no"],
        "total_liabilities": liabilities,
        "total_equity": equity,
        "accounting_debt_to_equity": (
            liabilities / equity
        ),
    }


def get_interest_bearing_debt(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> dict:
    rows = fetch_financial_statements_from_db(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
        sj_div="BS",
    )

    if not rows:
        raise CapitalStructureAnalysisError(
            "재무상태표 데이터가 없습니다."
        )

    debt_rows = (
        select_interest_bearing_debt_accounts(
            rows
        )
    )

    if not debt_rows:
        raise CapitalStructureAnalysisError(
            "이자부부채 계정을 찾지 못했습니다."
        )

    interest_bearing_debt = sum(
        row["thstrm_amount"]
        for row in debt_rows
        if row.get("thstrm_amount") is not None
    )

    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "rcept_no": debt_rows[0]["rcept_no"],
        "interest_bearing_debt": (
            interest_bearing_debt
        ),
        "debt_accounts": [
            {
                "account_id": row.get(
                    "account_id"
                ),
                "account_nm": row.get(
                    "account_nm"
                ),
                "amount": row.get(
                    "thstrm_amount"
                ),
            }
            for row in debt_rows
        ],
    }


def _find_account(
    rows: list[dict],
    account_ids: set[str],
    account_names: set[str],
) -> dict | None:
    for row in rows:
        account_id = (
            row.get("account_id")
            or ""
        )

        if account_id in account_ids:
            return row

    for row in rows:
        account_name = (
            row.get("account_nm")
            or ""
        ).strip()

        if account_name in account_names:
            return row

    return None


def get_capital_structure_analysis(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> dict:
    capital_structure = get_capital_structure(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
    )

    interest_bearing_debt_result = (
        get_interest_bearing_debt(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )
    )

    total_liabilities = (
        capital_structure["total_liabilities"]
    )
    total_equity = (
        capital_structure["total_equity"]
    )
    interest_bearing_debt = (
        interest_bearing_debt_result[
            "interest_bearing_debt"
        ]
    )

    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "rcept_no": capital_structure[
            "rcept_no"
        ],
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "interest_bearing_debt": (
            interest_bearing_debt
        ),
        "accounting_debt_to_equity": (
            capital_structure[
                "accounting_debt_to_equity"
            ]
        ),
        "interest_bearing_debt_to_equity": (
            interest_bearing_debt
            / total_equity
        ),
        "interest_bearing_debt_ratio": (
            interest_bearing_debt
            / total_liabilities
        ),
        "debt_accounts": (
            interest_bearing_debt_result[
                "debt_accounts"
            ]
        ),
    }