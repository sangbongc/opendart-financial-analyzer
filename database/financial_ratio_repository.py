from collections.abc import Iterable
from datetime import datetime

from database.connection import get_connection


def _get_current_time() -> str:
    """
    현재 시각을 SQLite에 저장하기 좋은 문자열로 반환한다.
    """
    return datetime.now().isoformat(
        sep=" ",
        timespec="seconds",
    )


def upsert_financial_ratios(
    ratios: Iterable[dict],
) -> int:
    """
    계산된 재무비율을 저장하거나 갱신한다.

    동일한 기업, 사업연도, 보고서 코드, 재무제표 구분,
    비율 코드, 계산 버전의 데이터가 이미 존재하면
    기존 값을 갱신한다.

    저장 또는 갱신한 행 수를 반환한다.
    """
    ratio_rows = list(ratios)

    if not ratio_rows:
        return 0

    calculated_at = _get_current_time()

    values = [
        (
            row["corp_code"],
            row["bsns_year"],
            row["reprt_code"],
            row["fs_div"],
            row["ratio_code"],
            row["ratio_name"],
            row.get("ratio_value"),
            row.get("numerator_value"),
            row.get("denominator_value"),
            row.get("calculation_version", "v1"),
            row.get("calculated_at", calculated_at),
        )
        for row in ratio_rows
    ]

    connection = get_connection()

    try:
        connection.executemany(
            """
            INSERT INTO financial_ratio_results (
                corp_code,
                bsns_year,
                reprt_code,
                fs_div,
                ratio_code,
                ratio_name,
                ratio_value,
                numerator_value,
                denominator_value,
                calculation_version,
                calculated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT (
                corp_code,
                bsns_year,
                reprt_code,
                fs_div,
                ratio_code,
                calculation_version
            )
            DO UPDATE SET
                ratio_name = excluded.ratio_name,
                ratio_value = excluded.ratio_value,
                numerator_value = excluded.numerator_value,
                denominator_value = excluded.denominator_value,
                calculated_at = excluded.calculated_at
            """,
            values,
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return len(values)


def fetch_financial_ratios(
    corp_code: str,
    bsns_year: str,
    reprt_code: str | None = None,
    fs_div: str | None = None,
    ratio_code: str | None = None,
    calculation_version: str | None = None,
) -> list[dict]:
    """
    저장된 재무비율을 조건에 따라 조회한다.

    보고서 코드, 재무제표 구분, 비율 코드,
    계산 버전은 선택적으로 필터링할 수 있다.
    """
    query = """
        SELECT
            id,
            corp_code,
            bsns_year,
            reprt_code,
            fs_div,
            ratio_code,
            ratio_name,
            ratio_value,
            numerator_value,
            denominator_value,
            calculation_version,
            calculated_at
        FROM financial_ratio_results
        WHERE corp_code = ?
          AND bsns_year = ?
    """

    parameters: list[object] = [
        corp_code,
        bsns_year,
    ]

    if reprt_code is not None:
        query += " AND reprt_code = ?"
        parameters.append(reprt_code)

    if fs_div is not None:
        query += " AND fs_div = ?"
        parameters.append(fs_div)

    if ratio_code is not None:
        query += " AND ratio_code = ?"
        parameters.append(ratio_code)

    if calculation_version is not None:
        query += " AND calculation_version = ?"
        parameters.append(calculation_version)

    query += """
        ORDER BY
            reprt_code,
            fs_div,
            ratio_code
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            query,
            parameters,
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def fetch_financial_ratio(
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    ratio_code: str,
    calculation_version: str = "v1",
) -> dict | None:
    """
    특정 재무비율 한 건을 조회한다.
    """
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                id,
                corp_code,
                bsns_year,
                reprt_code,
                fs_div,
                ratio_code,
                ratio_name,
                ratio_value,
                numerator_value,
                denominator_value,
                calculation_version,
                calculated_at
            FROM financial_ratio_results
            WHERE corp_code = ?
              AND bsns_year = ?
              AND reprt_code = ?
              AND fs_div = ?
              AND ratio_code = ?
              AND calculation_version = ?
            """,
            (
                corp_code,
                bsns_year,
                reprt_code,
                fs_div,
                ratio_code,
                calculation_version,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def delete_financial_ratios(
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    calculation_version: str | None = None,
) -> int:
    """
    특정 기업과 보고서 기준으로 저장된 재무비율을 삭제한다.

    계산 버전을 전달하면 해당 버전의 결과만 삭제한다.
    삭제된 행 수를 반환한다.
    """
    query = """
        DELETE FROM financial_ratio_results
        WHERE corp_code = ?
          AND bsns_year = ?
          AND reprt_code = ?
          AND fs_div = ?
    """

    parameters: list[object] = [
        corp_code,
        bsns_year,
        reprt_code,
        fs_div,
    ]

    if calculation_version is not None:
        query += " AND calculation_version = ?"
        parameters.append(calculation_version)

    connection = get_connection()

    try:
        cursor = connection.execute(
            query,
            parameters,
        )

        connection.commit()

        return cursor.rowcount

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()