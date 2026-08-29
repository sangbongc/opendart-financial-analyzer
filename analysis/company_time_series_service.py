from __future__ import annotations

from typing import Any

from analysis.account_selector import (
    account_scope_priority,
    normalize_account_name,
)
from analysis.company_comparison_service import (
    ACCOUNT_ALIASES,
    CHANGE_COLUMNS,
    DISPLAY_COLUMNS,
    RATIO_COLUMNS,
)
from database.financial_ratio_repository import (
    fetch_financial_ratios_by_year_range,
)
from database.financial_statement_change_repository import (
    fetch_financial_statement_changes_by_year_range,
)


class CompanyTimeSeriesError(Exception):
    """
    한 기업의 재무지표 시계열 분석 과정에서 발생하는 오류.
    """


def analyze_company_time_series(
    corporation: dict[str, Any],
    start_year: str,
    end_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> dict[str, Any]:
    """
    한 기업의 여러 사업연도 재무비율과
    주요 계정 증감률을 시계열 형태로 구성한다.
    """
    _validate_conditions(
        corporation=corporation,
        start_year=start_year,
        end_year=end_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
    )

    corp_code = _normalize_corp_code(
        corporation.get("corp_code")
    )

    try:
        ratio_rows = fetch_financial_ratios_by_year_range(
            corp_code=corp_code,
            start_year=start_year,
            end_year=end_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

        change_rows = (
            fetch_financial_statement_changes_by_year_range(
                corp_code=corp_code,
                start_year=start_year,
                end_year=end_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
            )
        )

    except Exception as error:
        raise CompanyTimeSeriesError(
            "기업 시계열 데이터를 조회하는 중 "
            "오류가 발생했습니다."
        ) from error

    years = [
        str(year)
        for year in range(
            int(start_year),
            int(end_year) + 1,
        )
    ]

    rows = _build_time_series_rows(
        years=years,
        ratio_rows=ratio_rows,
        change_rows=change_rows,
    )

    missing_ratio_years = _find_missing_ratio_years(
        years=years,
        ratio_rows=ratio_rows,
    )

    missing_years = [
        row["bsns_year"]
        for row in rows
        if all(
            row.get(column_code) is None
            for column_code, _ in DISPLAY_COLUMNS
        )
    ]

    return {
        "corp_code": corp_code,
        "corp_name": str(
            corporation.get("corp_name")
            or corp_code
        ),
        "stock_code": (
            corporation.get("stock_code")
        ),
        "start_year": start_year,
        "end_year": end_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "columns": DISPLAY_COLUMNS,
        "rows": rows,
        "year_count": len(rows),
        "missing_years": missing_years,
        "missing_ratio_years": missing_ratio_years,
    }


def _find_missing_ratio_years(
    years: list[str],
    ratio_rows: list[dict[str, Any]],
) -> list[str]:
    """
    현재 정의된 재무비율 중 아직 계산 결과 행이
    저장되지 않은 사업연도를 찾는다.

    ratio_value가 None이어도 ratio_code 행이 존재하면
    이미 계산을 시도한 것으로 보고 누락으로 판단하지 않는다.
    """
    required_ratio_codes = {
        ratio_code
        for ratio_code, _ in RATIO_COLUMNS
    }

    stored_ratio_codes_by_year: dict[str, set[str]] = {
        year: set()
        for year in years
    }

    for ratio in ratio_rows:
        year = str(
            ratio.get("bsns_year") or ""
        ).strip()

        if year not in stored_ratio_codes_by_year:
            continue

        ratio_code = str(
            ratio.get("ratio_code") or ""
        ).strip()

        if not ratio_code:
            continue

        stored_ratio_codes_by_year[year].add(
            ratio_code
        )

    return [
        year
        for year in years
        if not required_ratio_codes.issubset(
            stored_ratio_codes_by_year[year]
        )
    ]


def _build_time_series_rows(
    years: list[str],
    ratio_rows: list[dict[str, Any]],
    change_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    조회 결과를 사업연도별 하나의 행으로 조립한다.
    """
    rows_by_year: dict[
        str,
        dict[str, Any],
    ] = {
        year: {
            "bsns_year": year,
            **{
                column_code: None
                for column_code, _ in DISPLAY_COLUMNS
            },
        }
        for year in years
    }

    _apply_ratio_rows(
        rows_by_year=rows_by_year,
        ratio_rows=ratio_rows,
    )

    changes_by_year: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for change in change_rows:
        year = str(
            change.get("bsns_year") or ""
        ).strip()

        if year not in rows_by_year:
            continue

        changes_by_year.setdefault(
            year,
            [],
        ).append(change)

    for year in years:
        selected_changes = _select_change_values(
            change_rows=changes_by_year.get(
                year,
                [],
            )
        )

        rows_by_year[year].update(
            selected_changes
        )

    return [
        rows_by_year[year]
        for year in years
    ]


def _apply_ratio_rows(
    rows_by_year: dict[str, dict[str, Any]],
    ratio_rows: list[dict[str, Any]],
) -> None:
    """
    저장된 재무비율을 사업연도별 행에 반영한다.
    """
    valid_ratio_codes = {
        ratio_code
        for ratio_code, _ in RATIO_COLUMNS
    }

    selected_rows: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}

    for ratio in ratio_rows:
        year = str(
            ratio.get("bsns_year") or ""
        ).strip()

        ratio_code = str(
            ratio.get("ratio_code") or ""
        ).strip()

        if year not in rows_by_year:
            continue

        if ratio_code not in valid_ratio_codes:
            continue

        key = (
            year,
            ratio_code,
        )

        previous = selected_rows.get(
            key
        )

        if previous is None:
            selected_rows[key] = ratio
            continue

        previous_calculated_at = str(
            previous.get("calculated_at")
            or ""
        )

        current_calculated_at = str(
            ratio.get("calculated_at")
            or ""
        )

        if (
            current_calculated_at
            > previous_calculated_at
        ):
            selected_rows[key] = ratio

    for (
        year,
        ratio_code,
    ), ratio in selected_rows.items():
        rows_by_year[year][
            ratio_code
        ] = _to_float(
            ratio.get("ratio_value")
        )


def _select_change_values(
    change_rows: list[dict[str, Any]],
) -> dict[str, float | None]:
    """
    한 사업연도의 계정 증감 결과 중
    주요 분석 계정의 대표값을 선택한다.

    기업 비교 서비스와 동일한 선택 원칙을 사용한다.
    """
    selected_values: dict[
        str,
        float | None,
    ] = {
        column_key: None
        for column_key, _ in CHANGE_COLUMNS
    }

    if not change_rows:
        return selected_values

    alias_to_key = {
        normalize_account_name(alias): column_key
        for column_key, aliases
        in ACCOUNT_ALIASES.items()
        for alias in aliases
    }

    alias_priority = {
        column_key: {
            normalize_account_name(alias): index
            for index, alias in enumerate(aliases)
        }
        for column_key, aliases
        in ACCOUNT_ALIASES.items()
    }

    selected_priority: dict[
        str,
        tuple[int, int, int, int],
    ] = {}

    for change in change_rows:
        normalized_name = normalize_account_name(
            change.get("account_nm")
        )

        column_key = alias_to_key.get(
            normalized_name
        )

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
                    change.get("sj_div")
                    or ""
                ),
            ),
            (
                account_scope_priority(
                    change,
                    prefer_current=prefer_current,
                )
                if prefer_current
                else 0
            ),
            alias_priority[
                column_key
            ].get(
                normalized_name,
                999,
            ),
            int(
                bool(
                    str(
                        change.get(
                            "account_detail"
                        )
                        or ""
                    ).strip()
                )
            ),
        )

        previous_priority = (
            selected_priority.get(
                column_key
            )
        )

        if (
            previous_priority is not None
            and previous_priority <= priority
        ):
            continue

        selected_priority[
            column_key
        ] = priority

        selected_values[
            column_key
        ] = _to_float(
            change.get("change_rate")
        )

    return selected_values


def _statement_priority(
    column_key: str,
    sj_div: str,
) -> int:
    """
    주요 계정별로 우선 사용할 재무제표 종류를 결정한다.
    """
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

    return priorities.get(
        sj_div,
        99,
    )


def _validate_conditions(
    corporation: dict[str, Any],
    start_year: str,
    end_year: str,
    reprt_code: str,
    fs_div: str,
) -> None:
    corp_code = _normalize_corp_code(
        corporation.get("corp_code")
    )

    if not corp_code:
        raise ValueError(
            "기업 고유번호가 필요합니다."
        )

    if not (
        len(start_year) == 4
        and start_year.isdigit()
    ):
        raise ValueError(
            "시작 사업연도는 4자리 숫자여야 합니다."
        )

    if not (
        len(end_year) == 4
        and end_year.isdigit()
    ):
        raise ValueError(
            "종료 사업연도는 4자리 숫자여야 합니다."
        )

    if int(start_year) > int(end_year):
        raise ValueError(
            "시작 사업연도는 종료 사업연도보다 "
            "클 수 없습니다."
        )

    if not reprt_code.strip():
        raise ValueError(
            "보고서 코드는 비어 있을 수 없습니다."
        )

    if fs_div not in {
        "CFS",
        "OFS",
    }:
        raise ValueError(
            "재무제표 구분은 CFS 또는 OFS여야 합니다."
        )


def _normalize_corp_code(
    corp_code: Any,
) -> str:
    text = str(
        corp_code or ""
    ).strip()

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

    except (
        TypeError,
        ValueError,
    ):
        return None