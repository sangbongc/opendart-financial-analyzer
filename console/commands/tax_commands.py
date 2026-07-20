from analysis.effective_tax_rate_service import (
    calculate_company_effective_tax_rate,
)
from console.corporation_selector import (
    select_corporation,
)
from console.commands.corporation_commands import (
    input_financial_statement_conditions,
)
from utils import format_amount


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