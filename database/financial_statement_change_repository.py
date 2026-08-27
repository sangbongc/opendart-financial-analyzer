from __future__ import annotations

from decimal import Decimal
from typing import Any

from database.connection import database_connection


DEFAULT_CALCULATION_VERSION = "v1"


class FinancialStatementChangeRepositoryError(Exception):
    """
    재무제표 증감 결과 저장 과정에서 발생하는 오류.
    """


def upsert_financial_statement_changes(
    results: list[dict[str, Any]],
    calculation_version: str = DEFAULT_CALCULATION_VERSION,
) -> int:
    """
    계정별 증감액과 증감률 결과를 일괄 저장한다.

    같은 원천 재무제표 행과 계산 버전의 결과가 이미 존재하면
    증감액과 증감률 및 계산 시각을 갱신한다.
    """
    if not results:
        return 0

    if not calculation_version.strip():
        raise FinancialStatementChangeRepositoryError(
            "calculation_version은 비어 있을 수 없습니다."
        )

    rows = [
        _build_insert_row(
            result=result,
            calculation_version=calculation_version,
        )
        for result in results
    ]

    query = """
        INSERT INTO financial_statement_changes (
            financial_statement_id,
            corp_code,
            bsns_year,
            reprt_code,
            fs_div,
            sj_div,
            account_id,
            account_nm,
            account_detail,
            change_amount,
            change_rate,
            calculation_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (
            financial_statement_id,
            calculation_version
        )
        DO UPDATE SET
            change_amount = excluded.change_amount,
            change_rate = excluded.change_rate,
            calculated_at = CURRENT_TIMESTAMP
    """

    try:
        with database_connection() as connection:
            before_changes = connection.total_changes
            connection.executemany(query, rows)
            return connection.total_changes - before_changes
    except FinancialStatementChangeRepositoryError:
        raise
    except Exception as error:
        raise FinancialStatementChangeRepositoryError(
            "재무제표 증감 결과 저장 중 오류가 발생했습니다."
        ) from error


def fetch_financial_statement_changes(
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    sj_div: str | None = None,
    calculation_version: str = DEFAULT_CALCULATION_VERSION,
) -> list[dict[str, Any]]:
    """
    저장된 계정별 증감 결과를 조회한다.

    재무제표 종류를 전달하면 해당 재무제표만 조회하고,
    전달하지 않으면 모든 재무제표 종류를 조회한다.
    """
    query = """
        SELECT
            fsc.id,
            fsc.financial_statement_id,
            fsc.corp_code,
            fsc.bsns_year,
            fsc.reprt_code,
            fsc.fs_div,
            fsc.sj_div,
            fsc.account_id,
            fsc.account_nm,
            fsc.account_detail,
            fs.thstrm_amount AS current_amount,
            fs.frmtrm_amount AS previous_amount,
            fsc.change_amount,
            fsc.change_rate,
            fsc.calculation_version,
            fsc.calculated_at,
            fs.ord
        FROM financial_statement_changes AS fsc
        JOIN financial_statements AS fs
          ON fs.id = fsc.financial_statement_id
        WHERE fsc.corp_code = ?
          AND fsc.bsns_year = ?
          AND fsc.reprt_code = ?
          AND fsc.fs_div = ?
          AND fsc.calculation_version = ?
    """

    parameters: list[object] = [
        corp_code,
        bsns_year,
        reprt_code,
        fs_div,
        calculation_version,
    ]

    if sj_div is not None:
        query += """
          AND fsc.sj_div = ?
        """
        parameters.append(sj_div)

    query += """
        ORDER BY
            fsc.sj_div,
            fs.ord,
            fs.id
    """

    try:
        with database_connection() as connection:
            cursor = connection.execute(
                query,
                parameters,
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    except Exception as error:
        raise FinancialStatementChangeRepositoryError(
            "재무제표 증감 결과 조회 중 오류가 발생했습니다."
        ) from error


def _build_insert_row(
    result: dict[str, Any],
    calculation_version: str,
) -> tuple[Any, ...]:
    required_fields = (
        "financial_statement_id",
        "corp_code",
        "bsns_year",
        "reprt_code",
        "fs_div",
        "sj_div",
        "account_nm",
    )

    for field in required_fields:
        value = result.get(field)
        if value is None or str(value).strip() == "":
            raise FinancialStatementChangeRepositoryError(
                f"{field}가 없어 증감 결과를 저장할 수 없습니다."
            )

    return (
        int(result["financial_statement_id"]),
        str(result["corp_code"]),
        str(result["bsns_year"]),
        str(result["reprt_code"]),
        str(result["fs_div"]),
        str(result["sj_div"]),
        str(result.get("account_id") or ""),
        str(result["account_nm"]),
        str(result.get("account_detail") or ""),
        _decimal_to_int(result.get("change_amount")),
        _decimal_to_float(result.get("change_ratio")),
        calculation_version,
    )


def _decimal_to_int(
    value: Decimal | int | None,
) -> int | None:
    if value is None:
        return None
    return int(value)


def _decimal_to_float(
    value: Decimal | float | int | None,
) -> float | None:
    if value is None:
        return None
    return float(value)