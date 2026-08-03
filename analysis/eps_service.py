from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)


_BASIC_EPS_IDS = {
    "ifrs-full_BasicEarningsLossPerShare",
    "dart_BasicEarningsLossPerShare",
}
_DILUTED_EPS_IDS = {
    "ifrs-full_DilutedEarningsLossPerShare",
    "dart_DilutedEarningsLossPerShare",
}

_BASIC_EPS_NAMES = (
    "기본주당이익",
    "기본주당순이익",
    "기본주당손익",
    "주당이익",
    "주당순이익",
)
_DILUTED_EPS_NAMES = (
    "희석주당이익",
    "희석주당순이익",
    "희석주당손익",
)


def get_eps_analysis(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> dict[str, Any]:
    """저장된 재무제표에서 공시된 기본·희석 EPS를 조회한다."""
    rows = fetch_financial_statements_from_db(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
    )

    basic_row = _select_eps_row(rows, diluted=False)
    diluted_row = _select_eps_row(rows, diluted=True)

    if basic_row is None and diluted_row is None:
        return {
            "basic_eps": None,
            "previous_basic_eps": None,
            "basic_eps_change_rate": None,
            "diluted_eps": None,
            "previous_diluted_eps": None,
            "diluted_eps_change_rate": None,
            "currency": None,
            "source_rows": [],
        }

    basic_current = _to_decimal(
        basic_row.get("thstrm_amount") if basic_row else None
    )
    basic_previous = _to_decimal(
        basic_row.get("frmtrm_amount") if basic_row else None
    )
    diluted_current = _to_decimal(
        diluted_row.get("thstrm_amount") if diluted_row else None
    )
    diluted_previous = _to_decimal(
        diluted_row.get("frmtrm_amount") if diluted_row else None
    )

    return {
        "basic_eps": basic_current,
        "previous_basic_eps": basic_previous,
        "basic_eps_change_rate": _calculate_change_rate(
            basic_current,
            basic_previous,
        ),
        "diluted_eps": diluted_current,
        "previous_diluted_eps": diluted_previous,
        "diluted_eps_change_rate": _calculate_change_rate(
            diluted_current,
            diluted_previous,
        ),
        "currency": (
            (basic_row or diluted_row or {}).get("currency")
            or "KRW"
        ),
        "source_rows": [
            row
            for row in (basic_row, diluted_row)
            if row is not None
        ],
    }


def _select_eps_row(
    rows: list[dict[str, Any]],
    *,
    diluted: bool,
) -> dict[str, Any] | None:
    target_ids = _DILUTED_EPS_IDS if diluted else _BASIC_EPS_IDS
    target_names = _DILUTED_EPS_NAMES if diluted else _BASIC_EPS_NAMES

    candidates: list[tuple[int, dict[str, Any]]] = []

    for row in rows:
        account_id = str(row.get("account_id") or "")
        account_name = _normalize_name(row.get("account_nm"))
        statement_code = str(row.get("sj_div") or "")

        score = 0
        if account_id in target_ids:
            score += 100
        elif any(account_id.endswith(item.split("_", 1)[-1]) for item in target_ids):
            score += 80

        exact_name_match = any(
            account_name == _normalize_name(name)
            for name in target_names
        )
        partial_name_match = any(
            _normalize_name(name) in account_name
            for name in target_names
        )

        if exact_name_match:
            score += 60
        elif partial_name_match:
            score += 40

        if diluted and "희석" not in account_name and score < 80:
            continue
        if not diluted and "희석" in account_name:
            continue

        if statement_code in {"IS", "CIS"}:
            score += 10
        if row.get("thstrm_amount") not in {None, ""}:
            score += 5

        if score > 0:
            candidates.append((score, row))

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            str(item[1].get("rcept_no") or ""),
        ),
        reverse=True,
    )
    return candidates[0][1]


def _normalize_name(value: object) -> str:
    return "".join(str(value or "").split()).replace("(원)", "")


def _to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _calculate_change_rate(
    current: Decimal | None,
    previous: Decimal | None,
) -> Decimal | None:
    if current is None or previous in {None, Decimal("0")}:
        return None
    return ((current - previous) / abs(previous)) * Decimal("100")
