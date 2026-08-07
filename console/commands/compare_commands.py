from __future__ import annotations

from typing import Any

from analysis.company_comparison_service import (
    BASE_RATIO_COLUMNS,
    CHANGE_COLUMNS,
    RATIO_FORMATS,
    WORKING_CAPITAL_COLUMNS,
    CompanyComparisonError,
    compare_corporation_financial_data,
)
from console.commands.corporation_commands import (
    input_financial_statement_conditions,
)
from dart.corporation_service import (
    find_corporations_with_count,
)
from database.industry_repository import (
    IndustryRepositoryError,
    fetch_corporations_by_industry,
    fetch_industry_groups,
)
from utils import pad, truncate_text


COLUMN_WIDTH = 15
COMPANY_WIDTH = 16


def handle_compare_corporations() -> None:
    """
    여러 기업의 저장된 재무비율과 주요 계정 증감률을
    하나의 표로 비교하고 평균·중앙값을 출력한다.
    """
    print()
    print("[여러 기업 재무지표 비교]")
    print("-" * 60)

    conditions = input_financial_statement_conditions()
    corporations = _select_comparison_corporations()

    if not corporations:
        print("비교할 기업이 없어 작업을 종료합니다.")
        return

    sort_key, descending = _input_sort_condition()

    try:
        result = compare_corporation_financial_data(
            corporations=corporations,
            bsns_year=conditions["bsns_year"],
            reprt_code=conditions["reprt_code"],
            fs_div=conditions["fs_div"],
            sort_key=sort_key,
            descending=descending,
        )

    except (CompanyComparisonError, ValueError) as error:
        print(f"기업 비교 중 오류가 발생했습니다: {error}")
        return

    except Exception as error:
        print(
            "기업 비교 중 예상하지 못한 오류가 "
            f"발생했습니다: {error}"
        )
        return

    _print_comparison_result(result)


def _print_comparison_result(
    result: dict[str, Any],
) -> None:
    rows = result["rows"]
    summary = result["summary"]

    print()
    print("[비교 조건]")
    print("-" * 60)
    print(f"기업 수: {result['corporation_count']:,}")
    print(f"사업연도: {result['bsns_year']}")
    print(f"보고서 코드: {result['reprt_code']}")
    print(f"재무제표 구분: {result['fs_div']}")

    _print_comparison_table(
        title="재무비율 비교",
        rows=rows,
        summary=summary,
        columns=BASE_RATIO_COLUMNS,
    )

    _print_comparison_table(
        title="운전자본 효율성 비교",
        rows=rows,
        summary=summary,
        columns=WORKING_CAPITAL_COLUMNS,
    )

    _print_comparison_table(
        title="계정 증감률 비교",
        rows=rows,
        summary=summary,
        columns=CHANGE_COLUMNS,
    )

    if result["missing_corporations"]:
        print()
        print(
            "저장된 비교 데이터가 없는 기업: "
            + ", ".join(
                result["missing_corporations"]
            )
        )


def _select_comparison_corporations(
) -> list[dict[str, Any]]:
    """
    기업 직접 선택 또는 저장된 산업군 선택 방식으로
    비교 대상 기업 목록을 구성한다.
    """
    print()
    print("[비교 대상 선택]")
    print("-" * 60)
    print("1. 기업 직접 선택")
    print("2. 저장된 산업군 선택")

    selection = input(
        "선택하세요 [1]: "
    ).strip()

    if selection in {"", "1"}:
        return _input_corporations_until_stop()

    if selection == "2":
        return _select_corporations_by_industry()

    print("목록에 있는 번호를 입력하세요.")
    return []


def _select_corporations_by_industry(
) -> list[dict[str, Any]]:
    """
    저장된 산업군을 선택하고 해당 산업군의 기업 목록을
    비교 대상으로 반환한다.
    """
    try:
        groups = fetch_industry_groups()

    except IndustryRepositoryError as error:
        print(f"산업군 목록 조회 실패: {error}")
        return []

    if not groups:
        print("저장된 산업군이 없습니다.")
        return []

    print()
    print("[산업군 선택]")
    print("-" * 80)

    for index, group in enumerate(
        groups,
        start=1,
    ):
        print(
            f"{index}. {group['industry_name']} "
            f"[{group['industry_code']}] "
            f"({group['member_count']:,}개 기업)"
        )

    selection = input(
        "비교할 산업군 번호를 입력하세요 "
        "(취소: Enter): "
    ).strip()

    if not selection:
        return []

    try:
        selected_index = int(selection) - 1

    except ValueError:
        print("숫자로 입력해야 합니다.")
        return []

    if not 0 <= selected_index < len(groups):
        print("목록에 있는 번호를 입력하세요.")
        return []

    selected_group = groups[selected_index]

    try:
        corporations = fetch_corporations_by_industry(
            industry_id=selected_group["industry_id"]
        )

    except IndustryRepositoryError as error:
        print(f"산업군 기업 목록 조회 실패: {error}")
        return []

    if not corporations:
        print(
            f"{selected_group['industry_name']} 산업군에 "
            "등록된 기업이 없습니다."
        )
        return []

    print()
    print(
        f"선택 산업군: "
        f"{selected_group['industry_name']} "
        f"({len(corporations):,}개 기업)"
    )

    for corporation in corporations:
        print(
            f"- {corporation['corp_name']} "
            f"({corporation['corp_code']})"
        )

    return corporations


def _input_sort_condition() -> tuple[str, bool]:
    print()
    print("[정렬 기준]")
    print("1. 기업명")
    print("2. ROA")
    print("3. 재고증감률")
    print("4. 매출증감률")

    selection = input(
        "정렬 기준을 선택하세요 [1]: "
    ).strip()

    mapping = {
        "": ("corp_name", False),
        "1": ("corp_name", False),
        "2": ("ROA", True),
        "3": ("INVENTORY_CHANGE", True),
        "4": ("REVENUE_CHANGE", True),
    }

    if selection not in mapping:
        print(
            "올바르지 않은 입력이므로 "
            "기업명순으로 정렬합니다."
        )
        return "corp_name", False

    return mapping[selection]


def _input_corporations_until_stop() -> list[dict[str, Any]]:
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


def _format_percentage(
    value: Any,
) -> str:
    if value is None:
        return "-"

    return f"{float(value):+.2f}%"


def _format_comparison_value(
    column_code: str,
    value: Any,
) -> str:
    if value is None:
        return "-"

    format_type = RATIO_FORMATS.get(
        column_code,
        "percentage",
    )

    if format_type == "turnover":
        return f"{float(value):.2f}회"

    if format_type == "days":
        return f"{float(value):.2f}일"

    return _format_percentage(value)


def _print_comparison_table(
    title: str,
    rows: list[dict[str, Any]],
    summary: dict[str, dict[str, Any]],
    columns: tuple[tuple[str, str], ...],
) -> None:
    line_width = (
        COMPANY_WIDTH
        + len(columns) * (COLUMN_WIDTH + 2)
    )

    print()
    print(f"[{title}]")
    print("-" * line_width)

    print(
        f"{pad('기업명', COMPANY_WIDTH)}  "
        + "  ".join(
            pad(label, COLUMN_WIDTH)
            for _, label in columns
        )
    )

    print("-" * line_width)

    for row in rows:
        company_name = truncate_text(
            str(row["corp_name"]),
            COMPANY_WIDTH,
        )

        values = [
            _format_comparison_value(
                column_code=column_code,
                value=row.get(column_code),
            )
            for column_code, _ in columns
        ]

        print(
            f"{pad(company_name, COMPANY_WIDTH)}  "
            + "  ".join(
                pad(value, COLUMN_WIDTH)
                for value in values
            )
        )

    print("-" * line_width)

    for summary_name, summary_key in (
        ("평균", "mean"),
        ("중앙값", "median"),
        ("표준편차", "stdev"),
        ("최소값", "min"),
        ("최대값", "max"),
    ):
        values = [
            _format_comparison_value(
                column_code=column_code,
                value=summary[column_code][summary_key],
            )
            for column_code, _ in columns
        ]

        print(
            f"{pad(summary_name, COMPANY_WIDTH)}  "
            + "  ".join(
                pad(value, COLUMN_WIDTH)
                for value in values
            )
        )

    counts = [
        str(summary[column_code]["count"])
        for column_code, _ in columns
    ]

    print(
        f"{pad('표본 수', COMPANY_WIDTH)}  "
        + "  ".join(
            pad(value, COLUMN_WIDTH)
            for value in counts
        )
    )