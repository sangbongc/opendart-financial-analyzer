from __future__ import annotations

from typing import Any

from database.connection import database_connection


class IndustryRepositoryError(Exception):
    """산업군 및 산업군별 기업 목록 저장·조회 오류."""


def create_industry_group(
    industry_code: str,
    industry_name: str,
    description: str | None = None,
) -> int:
    normalized_code = industry_code.strip().upper()
    normalized_name = industry_name.strip()
    normalized_description = (
        description.strip()
        if description is not None
        else None
    )

    if not normalized_code:
        raise IndustryRepositoryError(
            "industry_code는 비어 있을 수 없습니다."
        )

    if not normalized_name:
        raise IndustryRepositoryError(
            "industry_name은 비어 있을 수 없습니다."
        )

    try:
        with database_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO industry_groups (
                    industry_code,
                    industry_name,
                    description
                )
                VALUES (?, ?, ?)
                """,
                (
                    normalized_code,
                    normalized_name,
                    normalized_description,
                ),
            )
            return int(cursor.lastrowid)
    except Exception as error:
        raise IndustryRepositoryError(
            "산업군 생성 중 오류가 발생했습니다."
        ) from error


def fetch_industry_groups() -> list[dict[str, Any]]:
    try:
        with database_connection() as connection:
            cursor = connection.execute(
                """
                SELECT
                    g.industry_id,
                    g.industry_code,
                    g.industry_name,
                    g.description,
                    g.created_at,
                    COUNT(m.corp_code) AS member_count
                FROM industry_groups AS g
                LEFT JOIN industry_group_members AS m
                  ON m.industry_id = g.industry_id
                GROUP BY
                    g.industry_id,
                    g.industry_code,
                    g.industry_name,
                    g.description,
                    g.created_at
                ORDER BY g.industry_name
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as error:
        raise IndustryRepositoryError(
            "산업군 목록 조회 중 오류가 발생했습니다."
        ) from error


def fetch_industry_group(
    industry_id: int,
) -> dict[str, Any] | None:
    try:
        with database_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    industry_id,
                    industry_code,
                    industry_name,
                    description,
                    created_at
                FROM industry_groups
                WHERE industry_id = ?
                """,
                (industry_id,),
            ).fetchone()

            return dict(row) if row is not None else None
    except Exception as error:
        raise IndustryRepositoryError(
            "산업군 조회 중 오류가 발생했습니다."
        ) from error


def add_corporation_to_industry(
    industry_id: int,
    corp_code: str,
) -> bool:
    normalized_corp_code = corp_code.strip().zfill(8)

    if not normalized_corp_code:
        raise IndustryRepositoryError(
            "corp_code는 비어 있을 수 없습니다."
        )

    try:
        with database_connection() as connection:
            before_changes = connection.total_changes
            connection.execute(
                """
                INSERT OR IGNORE INTO industry_group_members (
                    industry_id,
                    corp_code
                )
                VALUES (?, ?)
                """,
                (
                    industry_id,
                    normalized_corp_code,
                ),
            )
            return connection.total_changes > before_changes
    except Exception as error:
        raise IndustryRepositoryError(
            "산업군에 기업을 추가하는 중 오류가 발생했습니다."
        ) from error


def add_corporations_to_industry(
    industry_id: int,
    corp_codes: list[str],
) -> int:
    normalized_codes = list(
        dict.fromkeys(
            corp_code.strip().zfill(8)
            for corp_code in corp_codes
            if corp_code and corp_code.strip()
        )
    )

    if not normalized_codes:
        return 0

    try:
        with database_connection() as connection:
            before_changes = connection.total_changes
            connection.executemany(
                """
                INSERT OR IGNORE INTO industry_group_members (
                    industry_id,
                    corp_code
                )
                VALUES (?, ?)
                """,
                [
                    (industry_id, corp_code)
                    for corp_code in normalized_codes
                ],
            )
            return (
                connection.total_changes
                - before_changes
            )
    except Exception as error:
        raise IndustryRepositoryError(
            "산업군에 여러 기업을 추가하는 중 오류가 발생했습니다."
        ) from error


def fetch_corporations_by_industry(
    industry_id: int,
) -> list[dict[str, Any]]:
    try:
        with database_connection() as connection:
            cursor = connection.execute(
                """
                SELECT
                    c.corp_code,
                    c.corp_name,
                    c.stock_code,
                    c.modify_date,
                    c.is_active,
                    m.created_at AS added_at
                FROM industry_group_members AS m
                JOIN dart_corporations AS c
                  ON c.corp_code = m.corp_code
                WHERE m.industry_id = ?
                ORDER BY c.corp_name
                """,
                (industry_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as error:
        raise IndustryRepositoryError(
            "산업군별 기업 목록 조회 중 오류가 발생했습니다."
        ) from error


def remove_corporation_from_industry(
    industry_id: int,
    corp_code: str,
) -> bool:
    normalized_corp_code = corp_code.strip().zfill(8)

    try:
        with database_connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM industry_group_members
                WHERE industry_id = ?
                  AND corp_code = ?
                """,
                (
                    industry_id,
                    normalized_corp_code,
                ),
            )
            return cursor.rowcount > 0
    except Exception as error:
        raise IndustryRepositoryError(
            "산업군에서 기업을 제거하는 중 오류가 발생했습니다."
        ) from error


def delete_industry_group(
    industry_id: int,
) -> bool:
    try:
        with database_connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM industry_groups
                WHERE industry_id = ?
                """,
                (industry_id,),
            )
            return cursor.rowcount > 0
    except Exception as error:
        raise IndustryRepositoryError(
            "산업군 삭제 중 오류가 발생했습니다."
        ) from error