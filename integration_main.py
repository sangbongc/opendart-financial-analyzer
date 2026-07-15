from database.schema import create_tables

from dart.financial_statement_service import (
    sync_financial_statements,
)
from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)
from analysis.financial_ratio_service import (
    FinancialRatioCalculationError,
    calculate_financial_ratios,
)

from wcwidth import wcswidth

def truncate_text(
    text: str,
    width: int,
    suffix: str = "...",
) -> str:
    """
    문자열의 실제 콘솔 표시 폭이 width를 넘으면 잘라낸다.
    """
    if wcswidth(text) <= width:
        return text

    suffix_width = wcswidth(suffix)
    target_width = width - suffix_width

    result = ""
    current_width = 0

    for char in text:
        char_width = wcswidth(char)

        if char_width < 0:
            char_width = 0

        if current_width + char_width > target_width:
            break

        result += char
        current_width += char_width

    return result + suffix


def pad(text: str, width: int) -> str:
    text = truncate_text(text, width)

    return text + " " * max(
        0,
        width - wcswidth(text),
    )


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

            header_account = pad("계정과목", 40)

            print(
                f"{header_account}"
                f"{'당기 금액':>25}"
            )

            print("-" * 80)

        account = pad(
            str(row["account_nm"]),
            40,
        )

        amount = format_amount(
            row["thstrm_amount"]
        )

        print(
            f"{account}"
            f"{amount:>25}"
        )

def format_ratio(value: float | None) -> str:
    if value is None:
        return "계산 불가"

    return f"{value:,.2f}%"

def print_financial_ratios(
    result: dict,
) -> None:
    ratios = result["ratios"]

    ratio_names = {
        "operating_margin": "영업이익률",
        "net_profit_margin": "순이익률",
        "roa": "ROA",
        "roe": "ROE",
        "debt_ratio": "부채비율",
        "current_ratio": "유동비율",
    }

    print()
    print("[주요 재무비율]")
    print("-" * 40)

    for key, name in ratio_names.items():
        print(
            f"{pad(name, 20)}"
            f"{format_ratio(ratios[key]):>15}"
        )



def main() -> None:
    create_tables()

    # result = sync_financial_statements(
    #     corp_code="00126380",
    #     bsns_year="2025",
    # )

    # print("재무제표 동기화 완료")
    # print(f"수신 행 수: {result['received_count']:,}")
    # print(f"저장 행 수: {result['saved_count']:,}")
    # print(f"중복 제외: {result['ignored_count']:,}")

    
    # rows = fetch_financial_statements_from_db(
    #     corp_code="00126380",
    #     bsns_year="2025",
    #     reprt_code="11011",
    #     fs_div="CFS",
    # )

    # print(f"조회 행 수: {len(rows)}")

    # print_financial_statements(rows)

    rows = fetch_financial_statements_from_db(
        corp_code="00126380",
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
    )

    print(f"조회 행 수: {len(rows)}")

    print_financial_statements(rows)

    try:
        ratio_result = calculate_financial_ratios(
            rows
        )

    except FinancialRatioCalculationError as error:
        print()
        print(f"재무비율 계산 실패: {error}")

    else:
        print_financial_ratios(
            ratio_result
        )


if __name__ == "__main__":
    main()