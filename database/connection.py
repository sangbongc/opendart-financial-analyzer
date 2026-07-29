import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

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

@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """
    SQLite 연결과 트랜잭션 생명주기를 관리한다.

    - 정상 종료 시 커밋한다.
    - 예외 발생 시 롤백한 뒤 예외를 다시 전달한다.
    - 성공 여부와 관계없이 연결을 닫는다.
    """
    connection = get_connection()

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()