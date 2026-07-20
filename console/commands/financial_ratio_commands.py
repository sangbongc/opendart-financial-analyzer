from console.corporation_selector import(
    select_corporation
)
from console.commands.corporation_commands import (
    input_financial_statement_conditions,
)    
from analysis.financial_ratio_service import (
    FinancialRatioCalculationError,
    calculate_and_save_financial_ratios,
)
from analysis.account_change_ratio_service import (
    major_accounts_by_statement,
    get_account_change_ratios,
    get_combined_account_change_ratios,
    get_major_account_change_ratios,
)
from analysis.account_change_analysis import (
    analyze_major_account_changes,
    print_major_account_analyses,
    analyze_inventory_vs_revenue,
    _normalize_account_name,
    _find_account_result,
    print_inventory_vs_revenue_analysis,    
)
from dart.financial_change_ratio_service import (
    print_account_change_ratios
)
from database.financial_ratio_repository import fetch_financial_ratios

from utils import (
    REPORT_CODE_ALIASES,
    REPORT_CODE_NAMES,
    FS_DIV_ALIASES,
    truncate_text,
    pad,
    pad_right,
    format_amount,
)


def handle_calculate_financial_ratios() -> None:
        """
        기업과 재무제표 조건을 입력받아
        재무비율을 계산하고 저장한다.
        """
        corporation = select_corporation()

        if corporation is None:
            return

        conditions = (
            input_financial_statement_conditions()
        )

        print("\n[재무비율 계산 조건]")
        print("-" * 60)
        print(f"기업명: {corporation['corp_name']}")
        print(f"고유번호: {corporation['corp_code']}")
        print(f"사업연도: {conditions['bsns_year']}")
        print(f"보고서 코드: {conditions['reprt_code']}")
        print(f"재무제표 구분: {conditions['fs_div']}")

        try:
            result = calculate_and_save_financial_ratios(
                corp_code=corporation["corp_code"],
                bsns_year=conditions["bsns_year"],
                reprt_code=conditions["reprt_code"],
                fs_div=conditions["fs_div"],
            )

        except FinancialRatioCalculationError as error:
            print(f"\n재무비율 계산 실패: {error}")
            return

        except Exception as error:
            print(
                "\n재무비율 계산 중 예상하지 못한 "
                f"오류가 발생했습니다: {error}"
            )
            return

        print("\n[재무비율 계산 결과]")
        print("-" * 60)

        for ratio in result["ratios"]:
            print(
                f"{ratio['ratio_name']}: "
                f"{format_ratio(ratio['ratio_value'])}"
            )

        print("-" * 60)
        print(f"계산 비율 수: {result['calculated_count']}")
        print(f"저장 또는 갱신: {result['saved_count']}")


def handle_show_financial_ratios() -> None:
        """
        저장된 재무비율을 조회하여 출력한다.
        """
        corporation = select_corporation()

        if corporation is None:
            return

        conditions = (
            input_financial_statement_conditions()
        )

        try:
            ratios = fetch_financial_ratios(
                corp_code=corporation["corp_code"],
                bsns_year=conditions["bsns_year"],
                reprt_code=conditions["reprt_code"],
                fs_div=conditions["fs_div"],
            )

        except Exception as error:
            print(
                "\n재무비율 조회 중 예상하지 못한 "
                f"오류가 발생했습니다: {error}"
            )
            return

        print("\n[저장된 재무비율]")
        print("-" * 60)
        print(f"기업명: {corporation['corp_name']}")
        print(f"고유번호: {corporation['corp_code']}")
        print(f"사업연도: {conditions['bsns_year']}")
        print(f"보고서 코드: {conditions['reprt_code']}")
        print(f"재무제표 구분: {conditions['fs_div']}")
        print("-" * 60)

        if not ratios:
            print("조건에 해당하는 저장된 재무비율이 없습니다.")
            return

        for ratio in ratios:
            print(
                f"{ratio['ratio_name']}: "
                f"{format_ratio(ratio['ratio_value'])}"
            )

        print("-" * 60)
        print(f"조회 비율 수: {len(ratios)}")
    

@staticmethod
def format_ratio(
    value: float | None,
    ) -> str:
        """
        계산된 재무비율을 출력용 문자열로 변환한다.
        """
        if value is None:
            return "계산 불가"

        return f"{value:,.2f}%"


def handle_account_change_ratios() -> None:
        """
        저장된 재무제표를 기반으로 계정별 증감률을 계산하고 출력한다.
        """
        print()
        print("[계정별 증감률 조회]")
        print("-" * 60)

        corporation = select_corporation()

        if corporation is None:
            return

        bsns_year = input(
            "사업연도를 입력하세요: "
        ).strip()

        if not bsns_year:
            print("사업연도를 입력해야 합니다.")
            return

        reprt_code = "11011"

        fs_div = input(
            "재무제표 구분을 입력하세요 "
            "(CFS: 연결, OFS: 별도) [CFS]: "
        ).strip().upper()

        if not fs_div:
            fs_div = "CFS"

        sj_div = input(
            "재무제표 종류를 입력하세요 "
            "(BS: 재무상태표, IS: 손익계산서, "
            "CIS: 포괄손익계산서, CF: 현금흐름표): "
        ).strip().upper()

        if sj_div not in {
            "BS",
            "IS",
            "CIS",
            "CF",
        }:
            print("올바른 재무제표 종류를 입력하세요.")
            return

        try:
            results = get_account_change_ratios(
                corp_code=corporation["corp_code"],
                bsns_year=bsns_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
                sj_div=sj_div,
            )

            analysis_results = get_combined_account_change_ratios(
                corp_code=corporation["corp_code"],
                bsns_year=bsns_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
            )

        except Exception as error:
            print(
                "계정별 증감률 계산 중 "
                f"오류가 발생했습니다: {error}"
            )
            return

        # 사용자가 선택한 재무제표의 증감률 출력
        print_account_change_ratios(results)

        # 주요 계정의 개별 변동 분석
        major_analyses = analyze_major_account_changes(
            analysis_results
        )

        print_major_account_analyses(
            major_analyses
        )

        # 매출액과 재고자산 증감률 비교
        inventory_analysis = analyze_inventory_vs_revenue(
            analysis_results
        )

        print_inventory_vs_revenue_analysis(
            inventory_analysis
        )


def handle_major_account_change_ratios() -> None:
        """
        저장된 재무제표를 기반으로 주요 계정 증감률을 계산하고 출력한다.
        """
        print()
        print("[주요 계정 증감률 조회]")
        print("-" * 60)
        corporation = select_corporation()

        if corporation is None:
            return

        bsns_year = input(
            "사업연도를 입력하세요: "
        ).strip()

        if not bsns_year:
            print("사업연도를 입력해야 합니다.")
            return

        reprt_code = "11011"

        fs_div = input(
            "재무제표 구분을 입력하세요 "
            "(CFS: 연결, OFS: 별도) [CFS]: "
        ).strip().upper()

        if not fs_div:
            fs_div = "CFS"
        
        if fs_div not in {"CFS", "OFS"}:
            print("재무제표 구분은 CFS 또는 OFS만 입력할 수 있습니다.")
            return
        
        try:
            results = get_major_account_change_ratios(
                corp_code=corporation["corp_code"],
                bsns_year=bsns_year,
                major_accounts_by_statement=(
                    major_accounts_by_statement
                ),
                reprt_code=reprt_code,
                fs_div=fs_div,
            )

        except Exception as error:
            print(
                "주요 계정 증감률 계산 중 "
                f"오류가 발생했습니다: {error}"
            )
            return

        if not results:
            print()
            print("조회된 주요 계정 증감률이 없습니다.")
            print(
                "해당 사업연도와 재무제표 구분의 "
                "저장 데이터를 확인하세요."
            )
            return

        print()
        print(
            f"기업명: {corporation['corp_name']}"
        )
        print(f"사업연도: {bsns_year}")
        print(f"재무제표 구분: {fs_div}")
        print("-" * 60)

        statement_names = {
            "IS": "손익계산서",
            "BS": "재무상태표",
        }

        current_sj_div = None

        for row in results:
            sj_div = row["sj_div"]

            if sj_div != current_sj_div:
                current_sj_div = sj_div

                print()
                print(f"[{statement_names.get(sj_div, sj_div)}]")
                print("-" * 90)
                print(
                    f"{pad('계정명', 18)}  "
                    f"{pad('당기', 22)}  "
                    f"{pad('전기', 22)}  "
                    f"{pad('증감률', 10)}"
                )
                print("-" * 90)

            account_name = str(row.get("account_nm") or "-")
            current_amount = format_amount(row.get("current_amount"))
            previous_amount = format_amount(row.get("previous_amount"))

            change_ratio = row.get("change_ratio")
            if change_ratio is None:
                change_ratio_text = "-"
            else:
                change_ratio_text = f"{float(change_ratio):+.2f}%"

            print(
                f"{pad(account_name, 18)}  "
                f"{pad(current_amount, 22)}  "
                f"{pad(previous_amount, 22)}  "
                f"{pad(change_ratio_text, 10)}"
            )