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


def upsert_corporation(
    corp_code: str,
    corp_name: str,
    stock_code: str | None,
    modify_date: str | None,
    seen_at: str | None = None,
) -> None:
    """
    기업 정보를 저장하거나 갱신한다.

    - 존재하지 않는 corp_code이면 새로 저장한다.
    - 이미 존재하면 회사명, 종목코드, 수정일자를 갱신한다.
    - 다시 확인된 기업은 활성 상태로 변경한다.
    """
    if not corp_code:
        raise ValueError("corp_code는 비어 있을 수 없습니다.")

    if not corp_name:
        raise ValueError("corp_name은 비어 있을 수 없습니다.")

    current_time = seen_at or _get_current_time()

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO dart_corporations (
                corp_code,
                corp_name,
                stock_code,
                modify_date,
                is_active,
                first_seen_at,
                last_seen_at,
                deactivated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, NULL)

            ON CONFLICT(corp_code) DO UPDATE SET
                corp_name = excluded.corp_name,
                stock_code = excluded.stock_code,
                modify_date = excluded.modify_date,
                is_active = 1,
                last_seen_at = excluded.last_seen_at,
                deactivated_at = NULL
            """,
            (
                corp_code,
                corp_name,
                stock_code or None,
                modify_date or None,
                current_time,
                current_time,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def upsert_corporations(
    corporations: Iterable[dict],
    seen_at: str | None = None,
) -> int:
    """
    여러 기업 정보를 한 번의 트랜잭션으로 저장하거나 갱신한다.

    반환값은 처리된 기업 수이다.
    """
    current_time = seen_at or _get_current_time()

    records = []

    for corporation in corporations:
        corp_code = corporation.get("corp_code")
        corp_name = corporation.get("corp_name")

        if not corp_code:
            raise ValueError("corp_code는 비어 있을 수 없습니다.")

        if not corp_name:
            raise ValueError("corp_name은 비어 있을 수 없습니다.")

        records.append(
            (
                corp_code,
                corp_name,
                corporation.get("stock_code") or None,
                corporation.get("modify_date") or None,
                current_time,
                current_time,
            )
        )

    if not records:
        return 0

    connection = get_connection()

    try:
        connection.executemany(
            """
            INSERT INTO dart_corporations (
                corp_code,
                corp_name,
                stock_code,
                modify_date,
                is_active,
                first_seen_at,
                last_seen_at,
                deactivated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, NULL)

            ON CONFLICT(corp_code) DO UPDATE SET
                corp_name = excluded.corp_name,
                stock_code = excluded.stock_code,
                modify_date = excluded.modify_date,
                is_active = 1,
                last_seen_at = excluded.last_seen_at,
                deactivated_at = NULL
            """,
            records,
        )

        connection.commit()

        return len(records)

    finally:
        connection.close()


def fetch_corporation_by_corp_code(
    corp_code: str,
) -> dict | None:
    """
    DART 기업 고유번호로 기업 정보를 조회한다.
    """
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                corp_code,
                corp_name,
                stock_code,
                modify_date,
                is_active,
                first_seen_at,
                last_seen_at,
                deactivated_at
            FROM dart_corporations
            WHERE corp_code = ?
            """,
            (corp_code,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def fetch_corporation_by_stock_code(
    stock_code: str,
    active_only: bool = True,
) -> dict | None:
    """
    주식 종목코드로 DART 기업 정보를 조회한다.
    """
    connection = get_connection()

    try:
        query = """
            SELECT
                corp_code,
                corp_name,
                stock_code,
                modify_date,
                is_active,
                first_seen_at,
                last_seen_at,
                deactivated_at
            FROM dart_corporations
            WHERE stock_code = ?
        """

        parameters: list = [stock_code]

        if active_only:
            query += " AND is_active = 1"

        row = connection.execute(
            query,
            parameters,
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def deactivate_missing_corporations(
    active_corp_codes: Iterable[str],
    deactivated_at: str | None = None,
) -> int:
    """
    DB에는 존재하지만 최신 기업 목록에는 없는 기업을 비활성화한다.

    기업 데이터는 삭제하지 않는다.
    """
    current_time = deactivated_at or _get_current_time()
    active_codes = set(active_corp_codes)

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT corp_code
            FROM dart_corporations
            WHERE is_active = 1
            """
        ).fetchall()

        missing_codes = [
            row["corp_code"]
            for row in rows
            if row["corp_code"] not in active_codes
        ]

        if not missing_codes:
            return 0

        connection.executemany(
            """
            UPDATE dart_corporations
            SET
                is_active = 0,
                deactivated_at = ?
            WHERE corp_code = ?
            """,
            [
                (current_time, corp_code)
                for corp_code in missing_codes
            ],
        )

        connection.commit()

        return len(missing_codes)

    finally:
        connection.close()


def fetch_all_corporations(
    active_only: bool = True,
) -> list[dict]:
    """
    기업 목록 전체를 조회한다.
    """
    connection = get_connection()

    try:
        query = """
            SELECT
                corp_code,
                corp_name,
                stock_code,
                modify_date,
                is_active,
                first_seen_at,
                last_seen_at,
                deactivated_at
            FROM dart_corporations
        """

        if active_only:
            query += " WHERE is_active = 1"

        query += " ORDER BY corp_name"

        rows = connection.execute(query).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()
    
def search_corporations_by_name(
    keyword: str,
    active_only: bool = True,
    limit: int = 20,
) -> list[dict]:
    """
    기업명에 검색어가 포함된 기업 목록을 조회한다.

    검색어와 기업명이 정확히 일치하는 결과를 먼저 반환하고,
    나머지는 기업명 오름차순으로 정렬한다.
    """
    normalized_keyword = keyword.strip()

    if not normalized_keyword:
        raise ValueError(
            "기업명 검색어는 비어 있을 수 없습니다."
        )

    if not isinstance(limit, int):
        raise TypeError(
            "limit은 정수여야 합니다."
        )

    if limit <= 0:
        raise ValueError(
            "limit은 1 이상이어야 합니다."
        )

    connection = get_connection()

    try:
        query = """
            SELECT
                corp_code,
                corp_name,
                stock_code,
                modify_date,
                is_active,
                first_seen_at,
                last_seen_at,
                deactivated_at
            FROM dart_corporations
            WHERE corp_name LIKE ?
        """

        parameters: list = [
            f"%{normalized_keyword}%",
        ]

        if active_only:
            query += """
                AND is_active = 1
            """

        query += """
            ORDER BY
                CASE
                    WHEN corp_name = ? THEN 0
                    ELSE 1
                END,
                corp_name
            LIMIT ?
        """

        parameters.extend(
            [
                normalized_keyword,
                limit,
            ]
        )

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