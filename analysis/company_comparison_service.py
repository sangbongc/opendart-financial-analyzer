from __future__ import annotations

from statistics import (
    mean, 
    median,
    stdev,
)
from typing import Any

from database.company_comparison_repository import (
    fetch_comparison_account_changes,
    fetch_comparison_financial_ratios,
)
from analysis.account_selector import (
    account_scope_priority,
    normalize_account_name,
)


BASE_RATIO_COLUMNS: tuple[tuple[str, str], ...] = (
    ("GROSS_PROFIT_MARGIN", "매출총이익률"),
    ("OPERATING_MARGIN", "영업이익률"),
    ("NET_PROFIT_MARGIN", "순이익률"),
    ("ROA", "ROA"),
    ("ROE", "ROE"),
    ("DEBT_RATIO", "부채비율"),
    ("CURRENT_RATIO", "유동비율"),
)

WORKING_CAPITAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("INVENTORY_TURNOVER", "재고회전율"),
    ("DIO", "재고보유일수"),
    ("RECEIVABLE_TURNOVER", "채권회전율"),
    ("DSO", "채권회수일수"),
    ("PAYABLE_TURNOVER", "채무회전율"),
    ("DPO", "채무지급일수"),
    ("CCC", "현금전환주기"),
)

RATIO_COLUMNS: tuple[tuple[str, str], ...] = (
    *BASE_RATIO_COLUMNS,
    *WORKING_CAPITAL_COLUMNS,
)

RATIO_FORMATS: dict[str, str] = {
    "GROSS_PROFIT_MARGIN": "percentage",
    "OPERATING_MARGIN": "percentage",
    "NET_PROFIT_MARGIN": "percentage",
    "ROA": "percentage",
    "ROE": "percentage",
    "DEBT_RATIO": "percentage",
    "CURRENT_RATIO": "percentage",
    "INVENTORY_TURNOVER": "turnover",
    "DIO": "days",
    "RECEIVABLE_TURNOVER": "turnover",
    "DSO": "days",
    "PAYABLE_TURNOVER": "turnover",
    "DPO": "days",
    "CCC": "days",
}

ACCOUNT_ALIASES: dict[str, tuple[str, ...]] = {
    "REVENUE_CHANGE": (
        "매출액",
        "수익(매출액)",
        "영업수익",
        "수익",
        "매출",
    ),
    "COST_OF_SALES_CHANGE": (
        "매출원가",
    ),
    "OPERATING_PROFIT_CHANGE": (
        "영업이익",
        "영업이익(손실)",
        "영업손익",
        "영업순손익",
        "영업손실",
    ),
    "RECEIVABLE_CHANGE": (
        "매출채권",
        "단기매출채권",
        "유동매출채권",
        "매출채권및기타채권",
        "매출채권 및 기타채권",
        "유동매출채권및기타채권",
        "유동매출채권 및 기타채권",
        "매출채권및기타유동채권",
        "매출채권 및 기타유동채권",
        "매출채권과기타채권",
        "매출채권 및 기타수취채권",
    ),
    "INVENTORY_CHANGE": (
        "재고자산",
        "유동재고자산",
    ),
    "PPE_CHANGE": (
        "유형자산",
        "비유동유형자산",
    ),
    "PAYABLE_CHANGE": (
        "매입채무",
        "단기매입채무",
        "유동매입채무",
        "매입채무및기타채무",
        "매입채무 및 기타채무",
        "유동매입채무및기타채무",
        "유동매입채무 및 기타채무",
        "매입채무및기타유동채무",
        "매입채무 및 기타유동채무",
        "매입채무및기타금융부채",
        "매입채무 및 기타지급채무",
        
    ),
}

CHANGE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("REVENUE_CHANGE", "매출증감률"),
    ("COST_OF_SALES_CHANGE", "매출원가증감률"),
    (
        "OPERATING_PROFIT_CHANGE",
        "영업이익증감률",
    ),
    (
        "RECEIVABLE_CHANGE",
        "매출채권증감률",
    ),
    ("INVENTORY_CHANGE", "재고증감률"),
    ("PAYABLE_CHANGE", "매입채무증감률"),
    ("PPE_CHANGE", "유형자산증감률"),
)

DISPLAY_COLUMNS: tuple[tuple[str, str], ...] = (
    *RATIO_COLUMNS,
    *CHANGE_COLUMNS,
)


class CompanyComparisonError(Exception):
    """여러 기업의 재무지표 비교 과정에서 발생하는 오류."""


def compare_corporation_financial_data(
    corporations: list[dict[str, Any]],
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
    sort_key: str = "corp_name",
    descending: bool = False,
) -> dict[str, Any]:
    if not corporations:
        raise ValueError(
            "비교할 기업이 한 곳 이상 필요합니다."
        )

    unique_corporations = _deduplicate_corporations(
        corporations
    )
    corp_codes = [
        corporation["corp_code"]
        for corporation in unique_corporations
    ]

    try:
        ratio_rows = fetch_comparison_financial_ratios(
            corp_codes=corp_codes,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
            ratio_codes=tuple(
                code for code, _ in RATIO_COLUMNS
            ),
        )

        account_names = tuple(
            dict.fromkeys(
                alias
                for aliases in ACCOUNT_ALIASES.values()
                for alias in aliases
            )
        )

        change_rows = fetch_comparison_account_changes(
            corp_codes=corp_codes,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
            account_names=account_names,
        )

    except Exception as error:
        raise CompanyComparisonError(
            "기업 비교 데이터를 조회하는 중 오류가 발생했습니다."
        ) from error

    rows = _build_comparison_rows(
        corporations=unique_corporations,
        ratio_rows=ratio_rows,
        change_rows=change_rows,
    )

    _sort_comparison_rows(
        rows=rows,
        sort_key=sort_key,
        descending=descending,
    )

    return {
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "columns": DISPLAY_COLUMNS,
        "rows": rows,
        "summary": _calculate_summary(rows),
        "corporation_count": len(rows),
        "missing_corporations": [
            row["corp_name"]
            for row in rows
            if all(
                row[column_code] is None
                for column_code, _ in DISPLAY_COLUMNS
            )
        ],
    }


def _build_comparison_rows(
    corporations: list[dict[str, Any]],
    ratio_rows: list[dict[str, Any]],
    change_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows_by_code: dict[str, dict[str, Any]] = {}

    for corporation in corporations:
        corp_code = _normalize_corp_code(
            corporation.get("corp_code")
        )

        rows_by_code[corp_code] = {
            "corp_code": corp_code,
            "corp_name": str(
                corporation.get("corp_name") or corp_code
            ),
            **{
                column_code: None
                for column_code, _ in DISPLAY_COLUMNS
            },
        }

    valid_ratio_codes = {
        ratio_code
        for ratio_code, _ in RATIO_COLUMNS
    }

    for ratio in ratio_rows:
        corp_code = _normalize_corp_code(
            ratio.get("corp_code")
        )
        ratio_code = str(
            ratio.get("ratio_code") or ""
        ).strip()

        if corp_code not in rows_by_code:
            continue

        if ratio_code not in valid_ratio_codes:
            continue

        rows_by_code[corp_code][ratio_code] = _to_float(
            ratio.get("ratio_value")
        )

    alias_to_key = {
        normalize_account_name(alias): column_key
        for column_key, aliases in ACCOUNT_ALIASES.items()
        for alias in aliases
    }

    alias_priority = {
        column_key: {
            normalize_account_name(alias): index
            for index, alias in enumerate(aliases)
        }
        for column_key, aliases in ACCOUNT_ALIASES.items()
    }

    selected_priority: dict[
        tuple[str, str],
        tuple[int, int, int, int],
    ] = {}

    for change in change_rows:
        corp_code = _normalize_corp_code(
            change.get("corp_code")
        )
        normalized_name = normalize_account_name(
            change.get("account_nm")
        )
        column_key = alias_to_key.get(normalized_name)

        if corp_code not in rows_by_code:
            continue

        if column_key is None:
            continue

        prefer_current = column_key in {
            "RECEIVABLE_CHANGE",
            "INVENTORY_CHANGE",
            "PAYABLE_CHANGE",
        }

        priority = (
            _statement_priority(
                column_key=column_key,
                sj_div=str(
                    change.get("sj_div") or ""
                ),
            ),
            account_scope_priority(
                change,
                prefer_current=prefer_current,
            ) if prefer_current else 0,
            alias_priority[column_key].get(
                normalized_name,
                999,
            ),
            int(
                bool(
                    str(
                        change.get("account_detail") or ""
                    ).strip()
                )
            ),
        )

        selection_key = (
            corp_code,
            column_key,
        )
        previous_priority = selected_priority.get(
            selection_key
        )

        if (
            previous_priority is not None
            and previous_priority <= priority
        ):
            continue

        selected_priority[selection_key] = priority
        rows_by_code[corp_code][column_key] = _to_float(
            change.get("change_rate")
        )

    return list(rows_by_code.values())


def _calculate_summary(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, float | int | None]]:
    summary: dict[
        str,
        dict[str, float | int | None],
    ] = {}

    for column_code, _ in DISPLAY_COLUMNS:
        values = [
            float(row[column_code])
            for row in rows
            if row.get(column_code) is not None
        ]

        summary[column_code] = {
            "count": len(values),
            "mean": mean(values) if values else None,
            "median": median(values) if values else None,
            "stdev": (
                stdev(values)
                if len(values) >= 2
                else None
            ),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }

    return summary


def _sort_comparison_rows(
    rows: list[dict[str, Any]],
    sort_key: str,
    descending: bool,
) -> None:
    valid_keys = {
        "corp_name",
        *(
            code
            for code, _ in DISPLAY_COLUMNS
        ),
    }

    if sort_key not in valid_keys:
        raise ValueError(
            f"지원하지 않는 정렬 기준입니다: {sort_key}"
        )

    if sort_key == "corp_name":
        rows.sort(
            key=lambda row: str(row["corp_name"])
        )
        return

    rows.sort(
        key=lambda row: (
            row.get(sort_key) is None,
            (
                -float(row[sort_key])
                if descending
                else float(row[sort_key])
            )
            if row.get(sort_key) is not None
            else 0.0,
        )
    )


def _deduplicate_corporations(
    corporations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for corporation in corporations:
        corp_code = _normalize_corp_code(
            corporation.get("corp_code")
        )

        if not corp_code or corp_code in seen_codes:
            continue

        seen_codes.add(corp_code)

        normalized = dict(corporation)
        normalized["corp_code"] = corp_code
        unique.append(normalized)

    return unique


def _statement_priority(
    column_key: str,
    sj_div: str,
) -> int:
    income_statement_columns = {
        "REVENUE_CHANGE",
        "COST_OF_SALES_CHANGE",
        "OPERATING_PROFIT_CHANGE",
    }

    balance_sheet_columns = {
        "RECEIVABLE_CHANGE",
        "INVENTORY_CHANGE",
        "PPE_CHANGE",
        "PAYABLE_CHANGE",
    }

    if column_key in income_statement_columns:
        priorities = {
            "IS": 0,
            "CIS": 1,
        }

    elif column_key in balance_sheet_columns:
        priorities = {
            "BS": 0,
        }

    else:
        priorities = {}

    return priorities.get(sj_div, 99)


def _normalize_corp_code(
    corp_code: Any,
) -> str:
    text = str(corp_code or "").strip()

    if not text:
        return ""

    return text.zfill(8)


def _to_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None