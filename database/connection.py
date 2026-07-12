import sqlite3

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """
    OpenDART SQLite 데이터베이스 연결을 반환한다.

    DB 파일이 저장될 data 디렉터리가 없으면
    자동으로 생성한다.
    """
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(DB_PATH)

    # SELECT 결과를 튜플 대신 컬럼명으로 접근할 수 있게 한다.
    connection.row_factory = sqlite3.Row

    # SQLite에서 외래키 제약조건을 활성화한다.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection