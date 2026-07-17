import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

import database.financial_ratio_repository as repository


@pytest.fixture
def temporary_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Path]:
    """
    재무비율 Repository 테스트용 임시 SQLite DB를 생성한다.

    테스트가 실제 data/dart.db에 영향을 주지 않도록
    Repository의 get_connection을 임시 DB 연결 함수로 교체한다.
    """
    database_path = tmp_path / "test_dart.db"

    def get_test_connection() -> sqlite3.Connection:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    monkeypatch.setattr(
        repository,
        "get_connection",
        get_test_connection,
    )

    connection = get_test_connection()

    try:
        connection.execute(
            """
            CREATE TABLE dart_corporations (
                corp_code TEXT PRIMARY KEY,
                corp_name TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE financial_ratio_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                corp_code TEXT NOT NULL,
                bsns_year TEXT NOT NULL,
                reprt_code TEXT NOT NULL,
                fs_div TEXT NOT NULL,

                ratio_code TEXT NOT NULL,
                ratio_name TEXT NOT NULL,

                ratio_value REAL,
                numerator_value REAL,
                denominator_value REAL,

                calculation_version TEXT NOT NULL,
                calculated_at TEXT NOT NULL,

                FOREIGN KEY (corp_code)
                    REFERENCES dart_corporations(corp_code),

                UNIQUE (
                    corp_code,
                    bsns_year,
                    reprt_code,
                    fs_div,
                    ratio_code,
                    calculation_version
                )
            )
            """
        )

        connection.execute(
            """
            INSERT INTO dart_corporations (
                corp_code,
                corp_name
            )
            VALUES (?, ?)
            """,
            (
                "00126380",
                "삼성전자(주)",
            ),
        )

        connection.commit()

    finally:
        connection.close()

    yield database_path

def test_upsert_financial_ratios_inserts_rows(
    temporary_database: Path,
) -> None:
    """
    여러 재무비율이 정상적으로 저장되는지 확인한다.
    """
    ratios = [
        {
            "corp_code": "00126380",
            "bsns_year": "2025",
            "reprt_code": "11011",
            "fs_div": "CFS",
            "ratio_code": "OPERATING_MARGIN",
            "ratio_name": "영업이익률",
            "ratio_value": 8.5,
            "numerator_value": 85_000,
            "denominator_value": 1_000_000,
            "calculation_version": "v1",
        },
        {
            "corp_code": "00126380",
            "bsns_year": "2025",
            "reprt_code": "11011",
            "fs_div": "CFS",
            "ratio_code": "CURRENT_RATIO",
            "ratio_name": "유동비율",
            "ratio_value": 250.0,
            "numerator_value": 500_000,
            "denominator_value": 200_000,
            "calculation_version": "v1",
        },
    ]

    saved_count = repository.upsert_financial_ratios(
        ratios
    )

    assert saved_count == 2

    saved_ratios = repository.fetch_financial_ratios(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        calculation_version="v1",
    )

    assert len(saved_ratios) == 2

    assert saved_ratios[0]["ratio_code"] == "CURRENT_RATIO"
    assert saved_ratios[0]["ratio_value"] == 250.0

    assert (
        saved_ratios[1]["ratio_code"]
        == "OPERATING_MARGIN"
    )
    assert saved_ratios[1]["ratio_value"] == 8.5

def test_upsert_financial_ratios_returns_zero_when_empty(
    temporary_database: Path,
) -> None:
    """
    빈 데이터를 전달하면 DB 작업 없이 0을 반환하는지 확인한다.
    """
    saved_count = repository.upsert_financial_ratios([])

    assert saved_count == 0

    rows = repository.fetch_financial_ratios(
        corp_code="00126380",
        bsns_year="2025",
    )

    assert rows == []

def test_fetch_financial_ratio_returns_matching_row(
    temporary_database: Path,
) -> None:
    """
    식별 조건에 맞는 특정 재무비율 한 건을 조회하는지 확인한다.
    """
    repository.upsert_financial_ratios(
        [
            {
                "corp_code": "00126380",
                "bsns_year": "2025",
                "reprt_code": "11011",
                "fs_div": "CFS",
                "ratio_code": "ROA",
                "ratio_name": "총자산이익률",
                "ratio_value": 7.25,
                "numerator_value": 72_500,
                "denominator_value": 1_000_000,
                "calculation_version": "v2_average_balance",
            }
        ]
    )

    ratio = repository.fetch_financial_ratio(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        ratio_code="ROA",
        calculation_version="v2_average_balance",
    )

    assert ratio is not None
    assert ratio["ratio_code"] == "ROA"
    assert ratio["ratio_name"] == "총자산이익률"
    assert ratio["ratio_value"] == 7.25
    assert (
        ratio["calculation_version"]
        == "v2_average_balance"
    )

def test_fetch_financial_ratio_returns_none_when_not_found(
    temporary_database: Path,
) -> None:
    """
    조회 조건에 맞는 재무비율이 없으면 None을 반환하는지 확인한다.
    """
    ratio = repository.fetch_financial_ratio(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        ratio_code="NOT_FOUND",
    )

    assert ratio is None

def test_fetch_financial_ratios_applies_optional_filters(
    temporary_database: Path,
) -> None:
    """
    보고서 코드, 재무제표 구분, 비율 코드,
    계산 버전 필터가 정상적으로 적용되는지 확인한다.
    """
    repository.upsert_financial_ratios(
        [
            {
                "corp_code": "00126380",
                "bsns_year": "2025",
                "reprt_code": "11011",
                "fs_div": "CFS",
                "ratio_code": "ROA",
                "ratio_name": "총자산이익률",
                "ratio_value": 7.0,
                "numerator_value": 70,
                "denominator_value": 1_000,
                "calculation_version": "v1",
            },
            {
                "corp_code": "00126380",
                "bsns_year": "2025",
                "reprt_code": "11011",
                "fs_div": "CFS",
                "ratio_code": "ROA",
                "ratio_name": "총자산이익률",
                "ratio_value": 6.5,
                "numerator_value": 70,
                "denominator_value": 1_076.92,
                "calculation_version": "v2_average_balance",
            },
            {
                "corp_code": "00126380",
                "bsns_year": "2025",
                "reprt_code": "11011",
                "fs_div": "OFS",
                "ratio_code": "ROA",
                "ratio_name": "총자산이익률",
                "ratio_value": 5.0,
                "numerator_value": 50,
                "denominator_value": 1_000,
                "calculation_version": "v1",
            },
        ]
    )

    rows = repository.fetch_financial_ratios(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        ratio_code="ROA",
        calculation_version="v2_average_balance",
    )

    assert len(rows) == 1
    assert rows[0]["ratio_value"] == 6.5
    assert (
        rows[0]["calculation_version"]
        == "v2_average_balance"
    )

def test_delete_financial_ratios_deletes_matching_rows(
    temporary_database: Path,
) -> None:
    """
    특정 기업과 보고서의 재무비율을 삭제하는지 확인한다.
    """
    repository.upsert_financial_ratios(
        [
            {
                "corp_code": "00126380",
                "bsns_year": "2025",
                "reprt_code": "11011",
                "fs_div": "CFS",
                "ratio_code": "ROA",
                "ratio_name": "총자산이익률",
                "ratio_value": 7.0,
                "numerator_value": 70,
                "denominator_value": 1_000,
                "calculation_version": "v1",
            },
            {
                "corp_code": "00126380",
                "bsns_year": "2025",
                "reprt_code": "11011",
                "fs_div": "CFS",
                "ratio_code": "ROE",
                "ratio_name": "자기자본이익률",
                "ratio_value": 10.0,
                "numerator_value": 70,
                "denominator_value": 700,
                "calculation_version": "v1",
            },
        ]
    )

    deleted_count = repository.delete_financial_ratios(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
    )

    assert deleted_count == 2

    rows = repository.fetch_financial_ratios(
        corp_code="00126380",
        bsns_year="2025",
    )

    assert rows == []

def test_delete_financial_ratios_deletes_only_selected_version(
    temporary_database: Path,
) -> None:
    """
    계산 버전을 전달하면 해당 버전의 결과만 삭제하는지 확인한다.
    """
    repository.upsert_financial_ratios(
        [
            {
                "corp_code": "00126380",
                "bsns_year": "2025",
                "reprt_code": "11011",
                "fs_div": "CFS",
                "ratio_code": "ROA",
                "ratio_name": "총자산이익률",
                "ratio_value": 7.0,
                "numerator_value": 70,
                "denominator_value": 1_000,
                "calculation_version": "v1",
            },
            {
                "corp_code": "00126380",
                "bsns_year": "2025",
                "reprt_code": "11011",
                "fs_div": "CFS",
                "ratio_code": "ROA",
                "ratio_name": "총자산이익률",
                "ratio_value": 6.5,
                "numerator_value": 70,
                "denominator_value": 1_076.92,
                "calculation_version": "v2_average_balance",
            },
        ]
    )

    deleted_count = repository.delete_financial_ratios(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
        calculation_version="v1",
    )

    assert deleted_count == 1

    remaining_rows = repository.fetch_financial_ratios(
        corp_code="00126380",
        bsns_year="2025",
    )

    assert len(remaining_rows) == 1
    assert (
        remaining_rows[0]["calculation_version"]
        == "v2_average_balance"
    )

