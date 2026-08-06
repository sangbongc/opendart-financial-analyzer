from __future__ import annotations

from typing import Any

from analysis.batch_prepare_service import (
    prepare_multiple_financial_data,
)
from console.commands.corporation_commands import (
    input_financial_statement_conditions,
)
from dart.corporation_service import (
    find_corporations_with_count,
)


def handle_batch_prepare_financial_data() -> None:
    """
    공통 재무제표 조건을 한 번 입력받고,
    stop이 입력될 때까지 여러 기업을 선택한 뒤
    재무 분석 데이터를 일괄 준비한다.
    """
    print()
    print("[여러 기업 재무 분석 데이터 준비]")
    print("-" * 60)

    conditions = input_financial_statement_conditions()

    corporations = _input_corporations_until_stop()

    if not corporations:
        print("선택된 기업이 없어 작업을 종료합니다.")
        return

    print()
    print("[일괄 준비 조건]")
    print("-" * 60)
    print(f"기업 수: {len(corporations):,}")
    print(f"사업연도: {conditions['bsns_year']}")
    print(f"보고서 코드: {conditions['reprt_code']}")
    print(f"재무제표 구분: {conditions['fs_div']}")
    print("동시 작업 수: 3")
    print("API 요청 시작 간격: 0.4초")

    print()
    print("여러 기업의 데이터 준비를 시작합니다.")

    try:
        result = prepare_multiple_financial_data(
            corporations=corporations,
            bsns_year=conditions["bsns_year"],
            reprt_code=conditions["reprt_code"],
            fs_div=conditions["fs_div"],
            max_workers=3,
            request_interval=0.4,
        )

    except Exception as error:
        print(
            "여러 기업 데이터 준비 중 오류가 "
            f"발생했습니다: {error}"
        )
        return

    print()
    print("[일괄 준비 결과]")
    print("-" * 60)
    print(f"선택 기업 수: {result['requested_count']:,}")
    print(f"중복 제외 기업 수: {result['unique_count']:,}")
    print(f"성공: {result['success_count']:,}")
    print(f"실패: {result['failure_count']:,}")

    if result["successes"]:
        print()
        print("[성공 기업]")
        print("-" * 60)

        for item in result["successes"]:
            print(
                f"- {item['corp_name']} "
                f"({item['corp_code']}): "
                f"재무제표 {item['received_statement_count']:,}행 수신, "
                f"비율 {item['calculated_ratio_count']:,}개, "
                f"증감률 {item['calculated_change_count']:,}개"
            )

    if result["failures"]:
        print()
        print("[실패 기업]")
        print("-" * 60)

        stage_names = {
            "financial_statements_fetch": "재무제표 API 조회",
            "financial_statements_save": "재무제표 저장",
            "financial_ratios": "재무비율 계산·저장",
            "account_changes": "증감률 계산·저장",
        }

        for item in result["failures"]:
            stage_name = stage_names.get(
                item["stage"],
                item["stage"],
            )

            print(
                f"- {item['corp_name']} "
                f"({item['corp_code']}), "
                f"{stage_name}: {item['message']}"
            )


def _input_corporations_until_stop() -> list[dict[str, Any]]:
    """
    stop이 입력될 때까지 기업을 검색하고 선택한다.

    corp_code 기준으로 중복 선택을 방지한다.
    """
    selected: list[dict[str, Any]] = []
    selected_codes: set[str] = set()

    print()
    print(
        "기업명, 종목코드 또는 고유번호를 입력하세요. "
        "입력을 마치려면 stop을 입력하세요."
    )

    while True:
        keyword = input("기업> ").strip()

        if keyword.lower() == "stop":
            break

        if not keyword:
            print("검색어를 입력하세요.")
            continue

        corporation = _select_corporation_by_keyword(
            keyword
        )

        if corporation is None:
            continue

        corp_code = corporation["corp_code"]

        if corp_code in selected_codes:
            print(
                f"{corporation['corp_name']}은(는) "
                "이미 추가된 기업입니다."
            )
            continue

        selected_codes.add(corp_code)
        selected.append(corporation)

        print(
            f"추가됨: {corporation['corp_name']} "
            f"({corp_code})"
        )

    return selected


def _select_corporation_by_keyword(
    keyword: str,
) -> dict[str, Any] | None:
    """
    입력된 검색어로 기업을 찾고 한 기업을 선택한다.
    """
    try:
        result = find_corporations_with_count(
            keyword=keyword,
            limit=20,
        )

    except Exception as error:
        print(f"기업 검색 중 오류가 발생했습니다: {error}")
        return None

    corporations = result["corporations"]
    total_count = result["total_count"]

    if not corporations:
        print("검색 결과가 없습니다.")
        return None

    if len(corporations) == 1:
        return corporations[0]

    print()
    print("[기업 검색 결과]")
    print("-" * 80)

    for index, corporation in enumerate(
        corporations,
        start=1,
    ):
        stock_code = (
            corporation.get("stock_code")
            or "비상장"
        )

        print(
            f"{index}. {corporation['corp_name']} "
            f"/ 종목코드: {stock_code} "
            f"/ 고유번호: {corporation['corp_code']}"
        )

    if total_count > len(corporations):
        print(
            f"검색 결과 {total_count:,}건 중 "
            f"{len(corporations):,}건만 표시했습니다."
        )

    selection = input(
        "선택할 기업 번호를 입력하세요 "
        "(취소: Enter): "
    ).strip()

    if not selection:
        return None

    try:
        selected_index = int(selection) - 1

    except ValueError:
        print("숫자로 입력해야 합니다.")
        return None

    if not 0 <= selected_index < len(corporations):
        print("목록에 있는 번호를 입력하세요.")
        return None

    return corporations[selected_index]