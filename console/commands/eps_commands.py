from decimal import Decimal

from analysis.eps_service import get_eps_analysis
from console.commands.corporation_commands import (
    input_financial_statement_conditions,
)
from console.corporation_selector import select_corporation


def handle_show_eps() -> None:
    """기업과 보고서 조건을 입력받아 공시된 EPS를 출력한다."""
    print("\n[주당순이익(EPS) 조회]")
    print("-" * 60)

    corporation = select_corporation()
    if corporation is None:
        return

    conditions = input_financial_statement_conditions()

    try:
        result = get_eps_analysis(
            corp_code=corporation["corp_code"],
            bsns_year=conditions["bsns_year"],
            reprt_code=conditions["reprt_code"],
            fs_div=conditions["fs_div"],
        )
    except Exception as error:
        print(f"EPS 조회 중 오류가 발생했습니다: {error}")
        return

    if not result["source_rows"]:
        print("\n조회된 EPS 계정이 없습니다.")
        print("먼저 fs 명령으로 해당 재무제표를 동기화했는지 확인하세요.")
        return

    print()
    print(f"기업명: {corporation['corp_name']}")
    print(f"사업연도: {conditions['bsns_year']}")
    print(f"보고서 코드: {conditions['reprt_code']}")
    print(f"재무제표 구분: {conditions['fs_div']}")
    print("-" * 60)
    _print_eps_line("기본주당이익(EPS)", result["basic_eps"])
    _print_eps_line("전기 기본주당이익", result["previous_basic_eps"])
    _print_rate_line("기본 EPS 증감률", result["basic_eps_change_rate"])
    _print_eps_line("희석주당이익", result["diluted_eps"])
    _print_eps_line("전기 희석주당이익", result["previous_diluted_eps"])
    _print_rate_line("희석 EPS 증감률", result["diluted_eps_change_rate"])


def _print_eps_line(label: str, value: Decimal | None) -> None:
    formatted = "-" if value is None else f"{value:,.0f}원"
    print(f"{label:<28}{formatted:>20}")


def _print_rate_line(label: str, value: Decimal | None) -> None:
    formatted = "-" if value is None else f"{value:,.2f}%"
    print(f"{label:<28}{formatted:>20}")
