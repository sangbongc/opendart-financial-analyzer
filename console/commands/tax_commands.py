from analysis.effective_tax_rate_service import (
    calculate_company_effective_tax_rate,
)
from analysis.tax_account_change_service import (
    get_tax_account_changes,
)
from console.corporation_selector import (
    select_corporation,
)
from console.commands.corporation_commands import (
    input_financial_statement_conditions,
)
from utils import (
    format_amount,
    format_signed_amount,
    format_change_ratio,
)


def handle_calculate_effective_tax_rate() -> None:
    """
    기업과 재무제표 조건을 입력받아
    실효세율을 계산하고 출력한다.
    """
    print("\n[실효세율 계산]")
    print("-" * 60)

    corporation = select_corporation()

    if corporation is None:
        return

    conditions = input_financial_statement_conditions()

    try:
        result = calculate_company_effective_tax_rate(
            corp_code=corporation["corp_code"],
            bsns_year=conditions["bsns_year"],
            reprt_code=conditions["reprt_code"],
            fs_div=conditions["fs_div"],
        )

    except ValueError as error:
        print(f"실효세율을 계산할 수 없습니다: {error}")
        return

    except Exception as error:
        print(
            "실효세율 계산 중 예상하지 못한 "
            f"오류가 발생했습니다: {error}"
        )
        return

    print()
    print(f"기업명: {corporation['corp_name']}")
    print(f"사업연도: {conditions['bsns_year']}")
    print(
        "법인세비용: "
        f"{format_amount(result['tax_expense'])}"
    )
    print(
        "법인세비용차감전순이익: "
        f"{format_amount(result['profit_before_tax'])}"
    )

    effective_tax_rate = result["effective_tax_rate"]

    if effective_tax_rate is None:
        print(
            "실효세율: 계산 불가 "
            "(법인세비용차감전순이익이 0 이하)"
        )
        return

    print(f"실효세율: {effective_tax_rate:.2f}%")


def handle_tax_account_changes() -> None:
    """
    선택한 기업의 세무 관련 주요 계정 변동을 조회한다.

    이연법인세자산, 이연법인세부채 등 세무 관련 계정의
    당기 금액, 전기 금액, 증감액, 증감률을 출력한다.
    """
    print()
    print("[세무 관련 주요계정 변동 조회]")
    print("-" * 60)

    corporation = select_corporation()

    if corporation is None:
        return

    corp_code = corporation["corp_code"]
    corp_name = corporation["corp_name"]

    bsns_year = input(
        "사업연도를 입력하세요 [기본값: 2025]: "
    ).strip() or "2025"

    reprt_code = input(
        "보고서 코드를 입력하세요 [기본값: 11011]: "
    ).strip() or "11011"

    fs_div = (
        input(
            "재무제표 구분을 입력하세요 "
            "[CFS/OFS, 기본값: CFS]: "
        )
        .strip()
        .upper()
        or "CFS"
    )

    try:
        results = get_tax_account_changes(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

    except Exception as error:
        print(
            "세무 관련 주요계정 변동 조회 중 "
            f"오류가 발생했습니다: {error}"
        )
        return

    print()
    print("[조회 조건]")
    print("-" * 60)
    print(f"기업명: {corp_name}")
    print(f"사업연도: {bsns_year}")
    print(f"보고서 코드: {reprt_code}")
    print(f"재무제표 구분: {fs_div}")

    if not results:
        print()
        print(
            "조회된 세무 관련 주요계정 변동 내역이 없습니다."
        )
        print(
            "해당 기업의 계정명이 등록된 세무 계정명과 "
            "다를 수 있습니다."
        )
        return

    print()
    print("[세무 관련 주요계정 변동]")
    print("-" * 60)

    for index, row in enumerate(results, start=1):
        tax_account_name = str(
            row.get("tax_account_name") or "-"
        )

        account_name = str(
            row.get("account_nm") or "-"
        )

        current_amount = row.get("current_amount")
        previous_amount = row.get("previous_amount")
        change_amount = row.get("change_amount")
        change_ratio = row.get("change_ratio")

        print()
        print(f"{index}. {tax_account_name}")

        if account_name != tax_account_name:
            print(f"   실제 계정명: {account_name}")

        print(
            "   당기 금액: "
            f"{format_amount(current_amount)}원"
        )
        print(
            "   전기 금액: "
            f"{format_amount(previous_amount)}원"
        )
        print(
            "   증감액: "
            f"{format_signed_amount(change_amount)}원"
        )
        print(
            "   증감률: "
            f"{format_change_ratio(change_ratio)}"
        )