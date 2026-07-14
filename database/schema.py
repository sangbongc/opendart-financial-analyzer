import sqlite3

from database.connection import get_connection


def create_corporations_table(
    connection: sqlite3.Connection,
) -> None:
    """
    DART 기업 고유번호 목록을 저장하는 테이블을 생성한다.

    이미 테이블이 존재하면 새로 만들지 않는다.
    """
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

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_dart_corporations_corp_name
        ON dart_corporations(corp_name)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_dart_corporations_stock_code
        ON dart_corporations(stock_code)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_dart_corporations_is_active
        ON dart_corporations(is_active)
        """
    )


def create_financial_statement_tables(
    connection: sqlite3.Connection,
) -> None:
    """
    OpenDART 전체 재무제표 API에서 수집한 계정별 데이터를
    저장하는 테이블과 조회용 인덱스를 생성한다.

    이미 테이블과 인덱스가 존재하면 새로 만들지 않는다.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS financial_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            rcept_no TEXT NOT NULL,
            reprt_code TEXT NOT NULL,
            bsns_year TEXT NOT NULL,
            corp_code TEXT NOT NULL,

            fs_div TEXT NOT NULL,
            fs_nm TEXT,

            sj_div TEXT NOT NULL,
            sj_nm TEXT,

            account_id TEXT NOT NULL DEFAULT '',
            account_nm TEXT NOT NULL,
            account_detail TEXT NOT NULL DEFAULT '',

            thstrm_nm TEXT,
            thstrm_amount INTEGER,
            thstrm_add_amount INTEGER,

            frmtrm_nm TEXT,
            frmtrm_amount INTEGER,
            frmtrm_q_nm TEXT,
            frmtrm_q_amount INTEGER,
            frmtrm_add_amount INTEGER,

            bfefrmtrm_nm TEXT,
            bfefrmtrm_amount INTEGER,

            ord INTEGER,
            currency TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (corp_code)
                REFERENCES dart_corporations(corp_code),

            UNIQUE (
                rcept_no,
                fs_div,
                sj_div,
                account_id,
                account_nm,
                account_detail,
                ord
            )
        );


        CREATE INDEX IF NOT EXISTS
            idx_financial_statements_corp_year
        ON financial_statements(
            corp_code,
            bsns_year
        );


        CREATE INDEX IF NOT EXISTS
            idx_financial_statements_report
        ON financial_statements(
            corp_code,
            bsns_year,
            reprt_code,
            fs_div
        );


        CREATE INDEX IF NOT EXISTS
            idx_financial_statements_account
        ON financial_statements(
            corp_code,
            account_id
        );


        CREATE INDEX IF NOT EXISTS
            idx_financial_statements_account_name
        ON financial_statements(
            corp_code,
            account_nm
        );


        CREATE INDEX IF NOT EXISTS
            idx_financial_statements_receipt
        ON financial_statements(rcept_no);
        """
    )


def create_tables() -> None:
    """
    프로젝트에서 사용하는 모든 데이터베이스 테이블을 생성한다.

    하나의 데이터베이스 연결과 트랜잭션 안에서
    전체 테이블 생성 작업을 수행한다.
    """
    connection = get_connection()

    try:
        create_corporations_table(connection)
        create_financial_statement_tables(connection)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()