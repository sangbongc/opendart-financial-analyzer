from database.schema import create_tables

from dart.financial_statement_service import (
    sync_financial_statements,
)
from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)
from wcwidth import wcswidth

def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - wcswidth(text))

def format_amount(value: object) -> str:
    if value is None:
        return "-"

    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def print_financial_statements(
    rows: list[dict],
) -> None:
    if not rows:
        print("조회된 재무제표가 없습니다.")
        return

    current_statement_name: str | None = None

    for row in rows:
        statement_name = row["sj_nm"]

        if statement_name != current_statement_name:
            current_statement_name = statement_name

            print()
            print(f"[{statement_name}]")
            print("-" * 80)
            print(
                f"{'계정과목':<40}"
                f"{'당기 금액':>30}"
            )
            print("-" * 80)

        print(
            f"{row['account_nm']:<40}"
            f"{format_amount(row['thstrm_amount']):>30}"
        )



def main() -> None:
    create_tables()

    # result = sync_financial_statements(
    #     corp_code="00126380",   # 삼성전자
    #     bsns_year="2025",
    # )

    # print("재무제표 동기화 완료")
    # print(f"수신 행 수: {result['received_count']:,}")
    # print(f"저장 행 수: {result['saved_count']:,}")
    # print(f"중복 제외: {result['ignored_count']:,}")
    rows = fetch_financial_statements_from_db(
    corp_code="00126380",
    bsns_year="2025",
    reprt_code="11011",
    fs_div="CFS",
)

    print(
    f"{pad(row['account_nm'], 40)}"
    f"{format_amount(row['thstrm_amount']):>25}"
)


if __name__ == "__main__":
    main()