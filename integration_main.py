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

from decimal import Decimal, InvalidOperation

from analysis.account_change_ratio_service import (
    get_account_change_ratios,
)
import traceback

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
    """
    출력 왼쪽 정렬 기능
    """
    return text + " " * max(
        0,
        width - wcswidth(text),
    )

def pad_right(text: str, width: int) -> str:
    """
    한글 등 실제 출력 폭을 고려하여 오른쪽 정렬한다.
    """
    text = truncate_text(text, width)

    return " " * max(
        0,
        width - wcswidth(text),
    ) + text

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

def format_amount(value: object) -> str:
    """
    숫자 또는 Decimal 값을 천 단위 구분기호가 포함된 문자열로 변환한다.
    값이 없거나 숫자로 변환할 수 없으면 '-'를 반환한다.
    """
    if value is None:
        return "-"

    try:
        amount = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    return f"{amount:,.0f}"


def format_ratio(value: object) -> str:
    """
    증감률을 소수점 둘째 자리까지 표시한다.
    전기 금액이 0이어서 계산할 수 없는 경우 '-'를 반환한다.
    """
    if value is None:
        return "-"

    try:
        ratio = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    return f"{ratio:,.2f}%"


def print_account_change_ratios(
    results: list[dict],
) -> None:
    """
    계정별 증감률 계산 결과를 콘솔에 출력한다.
    """
    if not results:
        print("조회된 계정 증감률 데이터가 없습니다.")
        return

    formatted_rows = []

    for row in results:
        formatted_rows.append(
            {
                "account_name": row.get("account_nm") or "-",
                "current_amount": format_amount(
                    row.get("current_amount")
                ),
                "previous_amount": format_amount(
                    row.get("previous_amount")
                ),
                "change_amount": format_amount(
                    row.get("change_amount")
                ),
                "change_ratio": format_ratio(
                    row.get("change_ratio")
                ),
            }
        )

    name_width = max(
        28,
        max(
            wcswidth(row["account_name"])
            for row in formatted_rows
        ) + 2,
    )

    amount_width = max(
        20,
        max(
            wcswidth(value)
            for row in formatted_rows
            for value in (
                row["current_amount"],
                row["previous_amount"],
                row["change_amount"],
            )
        ) + 3,
    )

    ratio_width = max(
        10,
        max(
            wcswidth(row["change_ratio"])
            for row in formatted_rows
        ) + 3,
    )

    total_width = (
        name_width
        + amount_width * 3
        + ratio_width
    )

    print()
    print("[계정별 증감 분석]")
    print("-" * total_width)

    print(
        pad("계정명", name_width)
        + pad_right("당기 금액", amount_width)
        + pad_right("전기 금액", amount_width)
        + pad_right("증감액", amount_width)
        + pad_right("증감률", ratio_width)
    )

    print("-" * total_width)

    for row in formatted_rows:
        print(
            pad(row["account_name"], name_width)
            + pad_right(row["current_amount"], amount_width)
            + pad_right(row["previous_amount"], amount_width)
            + pad_right(row["change_amount"], amount_width)
            + pad_right(row["change_ratio"], ratio_width)
        )

    print("-" * total_width)
    print(f"총 계정 수: {len(results):,}개")


def main() -> None:
    create_tables()

    ##재무제표 동기화 테스트
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

    ##재무비율 계산 print 테스트
    # rows = fetch_financial_statements_from_db(
    #     corp_code="00126380",
    #     bsns_year="2025",
    #     reprt_code="11011",
    #     fs_div="CFS",
    # )

    # print(f"조회 행 수: {len(rows)}")

    # print_financial_statements(rows)

    # try:
    #     ratio_result = calculate_financial_ratios(
    #         rows
    #     )

    # except FinancialRatioCalculationError as error:
    #     print()
    #     print(f"재무비율 계산 실패: {error}")

    # else:
    #     print_financial_ratios(
    #         ratio_result
    #     )
    corp_code = "00126380"
    bsns_year = "2025"
    reprt_code = "11011"
    fs_div = "CFS"
    sj_div = "BS"

    print("계정별 증감률을 계산합니다.")
    print(f"기업 고유번호: {corp_code}")
    print(f"사업연도: {bsns_year}")
    print(f"보고서 코드: {reprt_code}")
    print(f"재무제표 구분: {fs_div}")
    print(f"재무제표 종류: {sj_div}")

    try:
        results = get_account_change_ratios(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
            sj_div=sj_div,
        )
    except Exception as error:
        print()
        print(
            "계정별 증감률을 계산하는 중 "
            f"오류가 발생했습니다: {error}"
        )
        traceback.print_exc()
        return

    print_account_change_ratios(results)


if __name__ == "__main__":
    main()