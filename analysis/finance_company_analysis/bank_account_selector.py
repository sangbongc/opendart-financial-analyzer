from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from analysis.account_selector import normalize_account_name


BANK_ACCOUNT_ALIASES: dict[str, tuple[str, ...]] = {
    # BS
    "total_assets": (
        "자산총계",
        "자산총액",
        "총자산",
    ),
    "total_liabilities": (
        "부채총계",
        "부채총액",
        "총부채",
    ),
    "total_equity": (
        "자본총계",
        "자본총액",
        "총자본",
    ),
    "cash_and_deposits": (
        "현금및예치금",
        "현금및상각후원가측정예치금",
        "현금및현금성자산",
    ),
    "loans": (
        "상각후원가측정대출채권",
        "상각후원가측정대출채권및기타금융자산",
        "상각후원가측정대출채권및기타금융채권",
        "상각후원가측정대출채권및기타채권",
    ),
    "fvpl_assets": (
        "당기손익-공정가치측정금융자산",
    ),
    "fvoci_assets": (
        "기타포괄손익-공정가치측정금융자산",
        "기타포괄손익-공정가치측정유가증권",
    ),
    "amortized_cost_securities": (
        "상각후원가측정유가증권",
        "상각후원가측정금융자산",
    ),
    "derivative_assets": (
        "파생상품자산",
        "파생상품자산(위험회피목적)",
        "위험회피회계파생상품자산",
    ),
    "deposits": (
        "예수부채",
        "예수금",
    ),
    "borrowings": (
        "차입부채",
    ),
    "bonds": (
        "사채",
        "발행사채",
    ),
    "fvpl_liabilities": (
        "당기손익-공정가치측정금융부채",
    ),
    "derivative_liabilities": (
        "파생상품부채",
        "파생상품부채(위험회피목적)",
        "위험회피회계파생상품부채",
    ),

    # IS / CIS
    "net_interest_income": (
        "순이자손익",
        "순이자이익",
    ),
    "net_fee_income": (
        "순수수료손익",
        "순수수료이익",
    ),
    "credit_loss": (
        "신용손실충당금(전)환입액",
        "신용손실충당금전입액",
        "신용손실에대한손상차손",
        "신용손실에대한손상차손전입액",
    ),
    "net_income": (
        "당기순이익",
        "연결당기순이익",
        "연결순이익",
        "당기연결순이익",
    ),
    "operating_profit": (
        "영업이익",
    ),
}


# 일부 금융지주는 대출채권 뒤에 "및 기타금융자산" 등을 붙인다.
# 정확 일치를 우선하고, 아래 항목만 제한적으로 prefix 일치를 허용한다.
BANK_ACCOUNT_PREFIX_ALIASES: dict[str, tuple[str, ...]] = {
    "loans": (
        "상각후원가측정대출채권및기타",
    ),
}


def _normalized_aliases(account_key: str) -> tuple[str, ...]:
    try:
        aliases = BANK_ACCOUNT_ALIASES[account_key]
    except KeyError as error:
        raise KeyError(
            f"정의되지 않은 은행 계정 key입니다: {account_key}"
        ) from error

    return tuple(
        normalize_account_name(alias)
        for alias in aliases
    )


def _match_priority(
    account_name: str,
    *,
    account_key: str,
) -> tuple[int, int] | None:
    """
    계정명이 alias와 얼마나 잘 일치하는지 우선순위를 반환한다.

    반환값이 낮을수록 우선한다.
    - (0, n): exact alias 일치
    - (1, n): 허용된 prefix alias 일치
    """
    normalized_name = normalize_account_name(account_name)
    aliases = _normalized_aliases(account_key)

    for index, alias in enumerate(aliases):
        if normalized_name == alias:
            return (0, index)

    prefix_aliases = tuple(
        normalize_account_name(alias)
        for alias in BANK_ACCOUNT_PREFIX_ALIASES.get(
            account_key,
            (),
        )
    )

    for index, prefix in enumerate(prefix_aliases):
        if normalized_name.startswith(prefix):
            return (1, index)

    return None


def find_bank_account_row(
    statements: Iterable[dict[str, Any]],
    *,
    account_key: str,
    statement_divisions: tuple[str, ...] | None = None,
) -> dict[str, Any] | None:
    """
    금융회사 재무제표에서 지정한 경제적 계정에 가장 적합한 행을 찾는다.

    계정명은 공통 normalize_account_name()으로 정규화하며,
    정확 일치를 prefix 일치보다 우선한다.
    """
    division_priority = {
        division: index
        for index, division in enumerate(
            statement_divisions or ()
        )
    }

    candidates: list[
        tuple[tuple[int, int], dict[str, Any]]
    ] = []

    for row in statements:
        sj_div = str(row.get("sj_div") or "")

        if (
            statement_divisions is not None
            and sj_div not in statement_divisions
        ):
            continue

        match_priority = _match_priority(
            str(row.get("account_nm") or ""),
            account_key=account_key,
        )

        if match_priority is None:
            continue

        candidates.append(
            (match_priority, row)
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            division_priority.get(
                str(item[1].get("sj_div") or ""),
                len(division_priority),
            ),
            item[0][0],
            item[0][1],
            bool(
                str(
                    item[1].get("account_detail") or ""
                ).strip()
            ),
            int(item[1].get("ord") or 0),
            str(item[1].get("account_id") or ""),
        )
    )

    return candidates[0][1]


def select_bank_account_rows(
    statements: Iterable[dict[str, Any]],
    *,
    account_keys: Iterable[str],
    statement_divisions: tuple[str, ...] | None = None,
) -> dict[str, dict[str, Any] | None]:
    """
    여러 은행 계정을 한 번에 선택한다.

    selector 자체는 금액을 해석하지 않고 행 선택만 담당한다.
    """
    statement_rows = list(statements)

    return {
        account_key: find_bank_account_row(
            statement_rows,
            account_key=account_key,
            statement_divisions=statement_divisions,
        )
        for account_key in account_keys
    }