
from console.commands.corporation_commands import (
    input_financial_statement_conditions,
)
from console.corporation_selector import (
    select_corporation,
)
from analysis.prepare_service import (
    prepare_financial_data,
    PrepareFinancialDataError,
)

def handle_prepare_financial_data() -> None:
    """
    기업과 재무제표 조건을 한 번 입력받아
    재무 분석에 필요한 데이터를 순서대로 준비한다.

    1. DART 재무제표 수집 및 저장
    2. 저장된 재무제표 기반 재무비율 계산 및 저장
    3. 저장된 재무제표 기반 계정별 증감률 계산 및 저장
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
    print("재무 분석 데이터 준비를 시작합니다.")

    try:
        result = prepare_financial_data(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

    except PrepareFinancialDataError as error:
        stage_names = {
            "financial_statements": "재무제표 수집 및 저장",
            "financial_ratios": "재무비율 계산 및 저장",
            "account_changes": "계정별 증감률 계산 및 저장",
        }

        stage_name = stage_names.get(
            error.stage,
            error.stage,
        )

        print()
        print(f"[준비 실패: {stage_name}]")
        print("-" * 60)
        print(error)
        return

    except ValueError as error:
        print()
        print(f"입력값 오류: {error}")
        return

    except Exception as error:
        print()
        print(
            "재무 분석 데이터 준비 중 예상하지 못한 "
            f"오류가 발생했습니다: {error}"
        )
        return

    summary = result["summary"]

    print()
    print("[재무제표 수집 및 저장]")
    print("-" * 60)
    print(
        f"수신 행 수: "
        f"{summary['received_statement_count']:,}"
    )
    print(
        f"신규 저장 행 수: "
        f"{summary['saved_statement_count']:,}"
    )
    print(
        f"중복 제외 행 수: "
        f"{summary['ignored_statement_count']:,}"
    )

    print()
    print("[재무비율 계산 및 저장]")
    print("-" * 60)
    print(
        f"계산 비율 수: "
        f"{summary['calculated_ratio_count']:,}"
    )
    print(
        f"저장 또는 갱신 수: "
        f"{summary['saved_ratio_count']:,}"
    )

    unavailable_ratios = (
        result["financial_ratios"].get(
            "unavailable_ratios",
            [],
        )
    )

    if unavailable_ratios:
        print(
            "계산 불가 비율: "
            + ", ".join(unavailable_ratios)
        )

    print()
    print("[계정별 증감률 계산 및 저장]")
    print("-" * 60)
    print(
        f"계산 및 저장 대상 계정 수: "
        f"{summary['calculated_change_count']:,}"
    )

    print()
    print("-" * 60)
    print("재무 분석 데이터 준비가 완료되었습니다.")