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

def create_financial_statement_tables(
    connection: sqlite3.Connection,
) -> None:
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
                REFERENCES corp_codes(corp_code),

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

        CREATE INDEX IF NOT EXISTS idx_financial_statements_corp_year
        ON financial_statements(
            corp_code,
            bsns_year
        );

        CREATE INDEX IF NOT EXISTS idx_financial_statements_report
        ON financial_statements(
            corp_code,
            bsns_year,
            reprt_code,
            fs_div
        );

        CREATE INDEX IF NOT EXISTS idx_financial_statements_account
        ON financial_statements(
            corp_code,
            account_id
        );

        CREATE INDEX IF NOT EXISTS idx_financial_statements_account_name
        ON financial_statements(
            corp_code,
            account_nm
        );

        CREATE INDEX IF NOT EXISTS idx_financial_statements_receipt
        ON financial_statements(rcept_no);
        """
    )


def create_tables() -> None:
    connection = get_connection()

    try:
        create_corporations_table()
        create_financial_statement_tables(connection)
        connection.commit()

    finally:
        connection.close()