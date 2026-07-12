from database.connection import get_connection


def create_corporations_table() -> None:
    """
    DART 기업 고유번호 목록을 저장하는 테이블을 생성한다.
    이미 존재하면 새로 만들지 않는다.
    """
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dart_corporations (
                corp_code TEXT PRIMARY KEY,
                corp_name TEXT NOT NULL,
                stock_code TEXT,
                modify_date TEXT,

                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),

                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                deactivated_at TEXT
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


def create_tables() -> None:
    """
    프로젝트에서 사용하는 모든 테이블을 생성한다.
    """
    create_corporations_table()