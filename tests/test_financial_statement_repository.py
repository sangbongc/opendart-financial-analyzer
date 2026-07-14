import sqlite3
from pathlib import Path

import pytest

from database import financial_statement_repository
from database import schema


@pytest.fixture
def test_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """
    각 테스트마다 독립된 임시 SQLite DB를 생성한다.
    """
    database_path = tmp_path / "test_dart.db"

    def get_test_connection() -> sqlite3.Connection:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(
        schema,
        "get_connection",
        get_test_connection,
    )

    monkeypatch.setattr(
        financial_statement_repository,
        "get_connection",
        get_test_connection,
    )

    schema.create_tables()

    connection = get_test_connection()

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
            """,
            (
                "00126380",
                "삼성전자(주)",
                "005930",
                "20260701",
                "2026-07-14 17:00:00",
                "2026-07-14 17:00:00",
            ),
        )

        connection.commit()

    finally:
        connection.close()

    return database_path


def make_financial_statement_row(
    account_id: str = "ifrs-full_Assets",
    account_nm: str = "자산총계",
    ord_value: int = 1,
) -> dict:
    """
    Repository 테스트에 사용할 정상 재무제표 행을 만든다.
    """
    return {
        "rcept_no": "20260311000514",
        "reprt_code": "11011",
        "bsns_year": "2025",
        "corp_code": "00126380",
        "fs_div": "CFS",
        "fs_nm": "연결재무제표",
        "sj_div": "BS",
        "sj_nm": "연결 재무상태표",
        "account_id": account_id,
        "account_nm": account_nm,
        "account_detail": None,
        "thstrm_nm": "제57기",
        "thstrm_amount": 455905980000000,
        "thstrm_add_amount": None,
        "frmtrm_nm": "제56기말",
        "frmtrm_amount": 448424507000000,
        "frmtrm_q_nm": None,
        "frmtrm_q_amount": None,
        "frmtrm_add_amount": None,
        "bfefrmtrm_nm": "제55기말",
        "bfefrmtrm_amount": 455105980000000,
        "ord": ord_value,
        "currency": "KRW",
    }


def test_save_financial_statements(
    test_database: Path,
) -> None:
    rows = [
        make_financial_statement_row(),
        make_financial_statement_row(
            account_id="ifrs-full_Liabilities",
            account_nm="부채총계",
            ord_value=2,
        ),
    ]

    saved_count = (
        financial_statement_repository
        .save_financial_statements(rows)
    )

    assert saved_count == 2

    stored_rows = (
        financial_statement_repository
        .fetch_financial_statements(
            corp_code="00126380",
            bsns_year="2025",
            reprt_code="11011",
            fs_div="CFS",
        )
    )

    assert len(stored_rows) == 2
    assert stored_rows[0]["corp_code"] == "00126380"

    account_names = {
        row["account_nm"]
        for row in stored_rows
    }

    assert account_names == {
        "자산총계",
        "부채총계",
    }


def test_duplicate_financial_statements_are_ignored(
    test_database: Path,
) -> None:
    rows = [
        make_financial_statement_row(),
    ]

    first_saved_count = (
        financial_statement_repository
        .save_financial_statements(rows)
    )

    second_saved_count = (
        financial_statement_repository
        .save_financial_statements(rows)
    )

    total_count = (
        financial_statement_repository
        .count_financial_statements(
            corp_code="00126380",
        )
    )

    assert first_saved_count == 1
    assert second_saved_count == 0
    assert total_count == 1


def test_save_empty_financial_statements_returns_zero(
    test_database: Path,
) -> None:
    saved_count = (
        financial_statement_repository
        .save_financial_statements([])
    )

    assert saved_count == 0


def test_account_id_and_detail_none_are_saved_as_empty_string(
    test_database: Path,
) -> None:
    row = make_financial_statement_row(
        account_id="",
    )

    row["account_id"] = None
    row["account_detail"] = None

    saved_count = (
        financial_statement_repository
        .save_financial_statements([row])
    )

    stored_rows = (
        financial_statement_repository
        .fetch_financial_statements(
            corp_code="00126380",
        )
    )

    assert saved_count == 1
    assert stored_rows[0]["account_id"] == ""
    assert stored_rows[0]["account_detail"] == ""


@pytest.mark.parametrize(
    "missing_field",
    [
        "rcept_no",
        "reprt_code",
        "bsns_year",
        "corp_code",
        "fs_div",
        "sj_div",
        "account_nm",
    ],
)
def test_save_raises_error_when_required_field_is_missing(
    test_database: Path,
    missing_field: str,
) -> None:
    row = make_financial_statement_row()
    row[missing_field] = ""

    with pytest.raises(
        ValueError,
        match=missing_field,
    ):
        financial_statement_repository.save_financial_statements(
            [row]
        )


def test_fetch_financial_statements_with_filters(
    test_database: Path,
) -> None:
    row = make_financial_statement_row()

    financial_statement_repository.save_financial_statements(
        [row]
    )

    matched_rows = (
        financial_statement_repository
        .fetch_financial_statements(
            corp_code="00126380",
            bsns_year="2025",
            reprt_code="11011",
            fs_div="CFS",
        )
    )

    unmatched_rows = (
        financial_statement_repository
        .fetch_financial_statements(
            corp_code="00126380",
            bsns_year="2024",
        )
    )

    assert len(matched_rows) == 1
    assert unmatched_rows == []


def test_fetch_financial_statement_accounts(
    test_database: Path,
) -> None:
    rows = [
        make_financial_statement_row(),
        make_financial_statement_row(
            account_id="ifrs-full_Liabilities",
            account_nm="부채총계",
            ord_value=2,
        ),
    ]

    financial_statement_repository.save_financial_statements(
        rows
    )

    accounts = (
        financial_statement_repository
        .fetch_financial_statement_accounts(
            corp_code="00126380",
            bsns_year="2025",
            reprt_code="11011",
            fs_div="CFS",
            account_name="자산총계",
        )
    )

    assert len(accounts) == 1
    assert accounts[0]["account_nm"] == "자산총계"
    assert accounts[0]["thstrm_amount"] == 455905980000000


def test_foreign_key_rejects_unknown_corporation(
    test_database: Path,
) -> None:
    row = make_financial_statement_row()
    row["corp_code"] = "99999999"

    with pytest.raises(sqlite3.IntegrityError):
        financial_statement_repository.save_financial_statements(
            [row]
        )