from collections.abc import Iterable
from typing import Any

from database.connection import get_connection


def _normalize_financial_statement(
    row: dict[str, Any],
) -> tuple:
    """
    파싱된 재무제표 행을 DB 저장용 튜플로 변환한다.

    account_id와 account_detail은 UNIQUE 제약조건이
    안정적으로 작동하도록 None 대신 빈 문자열로 저장한다.
    """
    required_fields = (
        "rcept_no",
        "reprt_code",
        "bsns_year",
        "corp_code",
        "fs_div",
        "sj_div",
        "account_nm",
    )

    for field in required_fields:
        if not row.get(field):
            raise ValueError(
                f"{field}는 비어 있을 수 없습니다."
            )

    return (
        row["rcept_no"],
        row["reprt_code"],
        row["bsns_year"],
        row["corp_code"],
        row["fs_div"],
        row.get("fs_nm"),
        row["sj_div"],
        row.get("sj_nm"),
        row.get("account_id") or "",
        row["account_nm"],
        row.get("account_detail") or "",
        row.get("thstrm_nm"),
        row.get("thstrm_amount"),
        row.get("thstrm_add_amount"),
        row.get("frmtrm_nm"),
        row.get("frmtrm_amount"),
        row.get("frmtrm_q_nm"),
        row.get("frmtrm_q_amount"),
        row.get("frmtrm_add_amount"),
        row.get("bfefrmtrm_nm"),
        row.get("bfefrmtrm_amount"),
        row.get("ord"),
        row.get("currency"),
    )


def save_financial_statements(
    financial_statements: Iterable[dict[str, Any]],
) -> int:
    """
    여러 재무제표 행을 한 번의 트랜잭션으로 저장한다.

    이미 같은 공시의 동일한 계정 행이 존재하면
    UNIQUE 제약조건에 따라 저장하지 않는다.

    반환값은 새로 저장된 행 수이다.
    """
    records = [
        _normalize_financial_statement(row)
        for row in financial_statements
    ]

    if not records:
        return 0

    connection = get_connection()

    try:
        before_changes = connection.total_changes

        connection.executemany(
            """
            INSERT OR IGNORE INTO financial_statements (
                rcept_no,
                reprt_code,
                bsns_year,
                corp_code,
                fs_div,
                fs_nm,
                sj_div,
                sj_nm,
                account_id,
                account_nm,
                account_detail,
                thstrm_nm,
                thstrm_amount,
                thstrm_add_amount,
                frmtrm_nm,
                frmtrm_amount,
                frmtrm_q_nm,
                frmtrm_q_amount,
                frmtrm_add_amount,
                bfefrmtrm_nm,
                bfefrmtrm_amount,
                ord,
                currency
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            records,
        )

        connection.commit()

        return connection.total_changes - before_changes

    finally:
        connection.close()


def fetch_financial_statements_from_db(
    corp_code: str,
    bsns_year: str | None = None,
    reprt_code: str | None = None,
    fs_div: str | None = None,
    sj_div: str | None = None,
) -> list[dict]:
    """
    기업의 재무제표 원본 행을 조회한다.

    사업연도, 보고서 코드, 연결·별도 구분은
    필요한 경우 선택적으로 적용한다.
    """
    if not corp_code:
        raise ValueError(
            "corp_code는 비어 있을 수 없습니다."
        )

    query = """
        SELECT
            id,
            rcept_no,
            reprt_code,
            bsns_year,
            corp_code,
            fs_div,
            fs_nm,
            sj_div,
            sj_nm,
            account_id,
            account_nm,
            account_detail,
            thstrm_nm,
            thstrm_amount,
            thstrm_add_amount,
            frmtrm_nm,
            frmtrm_amount,
            frmtrm_q_nm,
            frmtrm_q_amount,
            frmtrm_add_amount,
            bfefrmtrm_nm,
            bfefrmtrm_amount,
            ord,
            currency,
            created_at
        FROM financial_statements
        WHERE corp_code = ?
    """

    parameters: list[Any] = [corp_code]

    if bsns_year is not None:
        query += " AND bsns_year = ?"
        parameters.append(bsns_year)

    if reprt_code is not None:
        query += " AND reprt_code = ?"
        parameters.append(reprt_code)

    if fs_div is not None:
        query += " AND fs_div = ?"
        parameters.append(fs_div)
    if sj_div is not None:
        query += " AND sj_div = ?"
        parameters.append(sj_div)

    query += """
        ORDER BY
            bsns_year DESC,
            rcept_no DESC,
            fs_div,
            sj_div,
            ord,
            id
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


def fetch_financial_statement_accounts(
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    account_name: str,
) -> list[dict]:
    """
    기업 재무제표에서 특정 계정명을 조회한다.

    동일한 계정명이 여러 재무제표나 세부 항목에
    존재할 수 있으므로 목록으로 반환한다.
    """
    if not corp_code:
        raise ValueError(
            "corp_code는 비어 있을 수 없습니다."
        )

    if not bsns_year:
        raise ValueError(
            "bsns_year는 비어 있을 수 없습니다."
        )

    if not reprt_code:
        raise ValueError(
            "reprt_code는 비어 있을 수 없습니다."
        )

    if not fs_div:
        raise ValueError(
            "fs_div는 비어 있을 수 없습니다."
        )

    if not account_name:
        raise ValueError(
            "account_name은 비어 있을 수 없습니다."
        )

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                id,
                rcept_no,
                reprt_code,
                bsns_year,
                corp_code,
                fs_div,
                fs_nm,
                sj_div,
                sj_nm,
                account_id,
                account_nm,
                account_detail,
                thstrm_nm,
                thstrm_amount,
                thstrm_add_amount,
                frmtrm_nm,
                frmtrm_amount,
                frmtrm_q_nm,
                frmtrm_q_amount,
                frmtrm_add_amount,
                bfefrmtrm_nm,
                bfefrmtrm_amount,
                ord,
                currency,
                created_at
            FROM financial_statements
            WHERE corp_code = ?
              AND bsns_year = ?
              AND reprt_code = ?
              AND fs_div = ?
              AND account_nm = ?
            ORDER BY
                rcept_no DESC,
                sj_div,
                ord,
                id
            """,
            (
                corp_code,
                bsns_year,
                reprt_code,
                fs_div,
                account_name,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


def count_financial_statements(
    corp_code: str | None = None,
) -> int:
    """
    저장된 재무제표 행 수를 반환한다.

    corp_code가 주어지면 해당 기업의 행 수만 계산한다.
    """
    connection = get_connection()

    try:
        if corp_code is None:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM financial_statements
                """
            ).fetchone()

        else:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM financial_statements
                WHERE corp_code = ?
                """,
                (corp_code,),
            ).fetchone()

        return int(row["count"])

    finally:
        connection.close()