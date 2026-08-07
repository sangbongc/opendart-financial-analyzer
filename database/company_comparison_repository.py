from __future__ import annotations

from typing import Any

from database.connection import database_connection


def fetch_comparison_financial_ratios(
    corp_codes: list[str],
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    ratio_codes: tuple[str, ...],
) -> list[dict[str, Any]]:
    """
    여러 기업의 저장된 재무비율을 한 번에 조회한다.

    계산 버전을 고정하지 않고, 기업·연도·보고서·재무제표
    구분·비율 코드별로 가장 최근 계산 결과 한 건을 반환한다.
    """
    if not corp_codes or not ratio_codes:
        return []

    corp_placeholders = ", ".join(
        "?" for _ in corp_codes
    )
    ratio_placeholders = ", ".join(
        "?" for _ in ratio_codes
    )

    query = f"""
        WITH ranked_ratios AS (
            SELECT
                r.id,
                r.corp_code,
                c.corp_name,
                r.ratio_code,
                r.ratio_name,
                r.ratio_value,
                r.calculation_version,
                r.calculated_at,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        r.corp_code,
                        r.bsns_year,
                        r.reprt_code,
                        r.fs_div,
                        r.ratio_code
                    ORDER BY
                        r.calculated_at DESC,
                        r.id DESC
                ) AS row_number
            FROM financial_ratio_results AS r
            JOIN dart_corporations AS c
              ON c.corp_code = r.corp_code
            WHERE r.corp_code IN ({corp_placeholders})
              AND r.bsns_year = ?
              AND r.reprt_code = ?
              AND r.fs_div = ?
              AND r.ratio_code IN ({ratio_placeholders})
        )
        SELECT
            corp_code,
            corp_name,
            ratio_code,
            ratio_name,
            ratio_value,
            calculation_version,
            calculated_at
        FROM ranked_ratios
        WHERE row_number = 1
        ORDER BY
            corp_name,
            ratio_code
    """

    parameters: list[Any] = [
        *corp_codes,
        bsns_year,
        reprt_code,
        fs_div,
        *ratio_codes,
    ]

    with database_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def fetch_comparison_account_changes(
    corp_codes: list[str],
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    account_names: tuple[str, ...],
) -> list[dict[str, Any]]:
    """
    여러 기업의 저장된 계정별 증감률을 한 번에 조회한다.

    계산 버전을 고정하지 않고, 기업·연도·보고서·재무제표
    구분·재무제표 종류·계정별로 가장 최근 계산 결과
    한 건을 반환한다.
    """
    if not corp_codes or not account_names:
        return []

    corp_placeholders = ", ".join(
        "?" for _ in corp_codes
    )
    account_placeholders = ", ".join(
        "?" for _ in account_names
    )

    query = f"""
        WITH ranked_changes AS (
            SELECT
                s.id,
                s.corp_code,
                c.corp_name,
                s.sj_div,
                s.account_id,
                s.account_nm,
                s.account_detail,
                s.change_rate,
                s.calculation_version,
                s.calculated_at,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        s.corp_code,
                        s.bsns_year,
                        s.reprt_code,
                        s.fs_div,
                        s.sj_div,
                        s.account_id,
                        s.account_nm,
                        s.account_detail
                    ORDER BY
                        s.calculated_at DESC,
                        s.id DESC
                ) AS row_number
            FROM financial_statement_changes AS s
            JOIN dart_corporations AS c
              ON c.corp_code = s.corp_code
            WHERE s.corp_code IN ({corp_placeholders})
              AND s.bsns_year = ?
              AND s.reprt_code = ?
              AND s.fs_div = ?
              AND s.account_nm IN ({account_placeholders})
        )
        SELECT
            corp_code,
            corp_name,
            sj_div,
            account_id,
            account_nm,
            account_detail,
            change_rate,
            calculation_version,
            calculated_at
        FROM ranked_changes
        WHERE row_number = 1
        ORDER BY
            corp_name,
            sj_div,
            account_nm,
            account_detail
    """

    parameters: list[Any] = [
        *corp_codes,
        bsns_year,
        reprt_code,
        fs_div,
        *account_names,
    ]

    with database_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]