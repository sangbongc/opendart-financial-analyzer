from analysis.account_change_ratio_service import (
    AccountChangeRatioError,
    calculate_and_save_account_change_ratios,
)
from analysis.financial_ratio_service import (
    FinancialRatioCalculationError,
    calculate_and_save_financial_ratios,
)
from console.commands.corporation_commands import (
    input_financial_statement_conditions,
)
from console.corporation_selector import (
    select_corporation,
)
from dart.financial_statement_service import (
    sync_financial_statements,
)


def handle_prepare_financial_data() -> None:
    """
    기업과 재무제표 조건을 한 번 입력받아 다음 작업을
    순서대로 수행한다.

    1. DART 재무제표 수집 및 저장
    2. 저장된 재무제표 기반 재무비율 계산 및 저장
    3. 저장된 재무제표 기반 계정별 증감률 계산 및 저장

    모든 작업이 완료되면 계정별 증감률을 출력한다.
    """
    print()
    print("[재무 분석 데이터 준비]")
    print("-" * 60)

    corporation = select_corporation()

    if corporation is None:
        return

    conditions = input_financial_statement_conditions()

    corp_code = corporation["corp_code"]
    corp_name = corporation["corp_name"]
    bsns_year = conditions["bsns_year"]
    reprt_code = conditions["reprt_code"]
    fs_div = conditions["fs_div"]

    print()
    print("[준비 조건]")
    print("-" * 60)
    print(f"기업명: {corp_name}")
    print(f"고유번호: {corp_code}")
    print(f"사업연도: {bsns_year}")
    print(f"보고서 코드: {reprt_code}")
    print(f"재무제표 구분: {fs_div}")

    print()
    print("[1/3] 재무제표 수집 및 저장")
    print("-" * 60)

    try:
        statement_result = sync_financial_statements(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

    except Exception as error:
        print(
            "재무제표 수집 및 저장 중 오류가 "
            f"발생했습니다: {error}"
        )
        print(
            "원천 재무제표가 준비되지 않아 "
            "후속 계산을 중단합니다."
        )
        return

    print(
        f"수신 행 수: "
        f"{statement_result['received_count']:,}"
    )
    print(
        f"신규 저장 행 수: "
        f"{statement_result['saved_count']:,}"
    )
    print(
        f"중복 제외 행 수: "
        f"{statement_result['ignored_count']:,}"
    )

    print()
    print("[2/3] 재무비율 계산 및 저장")
    print("-" * 60)

    try:
        ratio_result = calculate_and_save_financial_ratios(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

    except FinancialRatioCalculationError as error:
        print(f"재무비율 계산 실패: {error}")
        print(
            "재무비율 계산이 완료되지 않아 "
            "후속 계산을 중단합니다."
        )
        return

    except Exception as error:
        print(
            "재무비율 계산 및 저장 중 예상하지 못한 "
            f"오류가 발생했습니다: {error}"
        )
        return

    print(
        f"계산 비율 수: "
        f"{ratio_result['calculated_count']:,}"
    )
    print(
        f"저장 또는 갱신 수: "
        f"{ratio_result['saved_count']:,}"
    )

    unavailable_ratios = ratio_result.get(
        "unavailable_ratios",
        [],
    )

    if unavailable_ratios:
        print(
            "계산 불가 비율: "
            + ", ".join(unavailable_ratios)
        )

    print()
    print("[3/3] 계정별 증감률 계산 및 저장")
    print("-" * 60)

    try:
        change_results = (
            calculate_and_save_account_change_ratios(
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
            )
        )

    except AccountChangeRatioError as error:
        print(f"계정별 증감률 계산 실패: {error}")
        return

    except Exception as error:
        print(
            "계정별 증감률 계산 및 저장 중 "
            f"예상하지 못한 오류가 발생했습니다: {error}"
        )
        return

    if not change_results:
        print(
            "계산할 수 있는 계정별 증감률이 없습니다."
        )
        return

    print(
        f"계산 및 저장 대상 계정 수: "
        f"{len(change_results):,}"
    )


    print()
    print("-" * 60)
    print("재무 분석 데이터 준비가 완료되었습니다.")