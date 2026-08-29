from __future__ import annotations

from typing import Any

from analysis.company_comparison_service import (
    BASE_RATIO_COLUMNS,
    CHANGE_COLUMNS,
    RATIO_FORMATS,
    WORKING_CAPITAL_COLUMNS,
)
from analysis.company_time_series_service import (
    CompanyTimeSeriesError,
    analyze_company_time_series,
)
from console.corporation_selector import (
    select_corporation,
)
from utils import (
    format_ratio,
    pad,
)


def handle_company_time_series() -> None:
    """
    기업과 사업연도 범위를 입력받아
    저장된 재무비율 및 주요 계정 증감률을
    시계열 형태로 조회한다.
    """
    print()
    print("[기업 시계열 분석]")
    print("-" * 60)

    corporation = select_corporation()

    if corporation is None:
        return

    start_year = input(
        "시작 사업연도를 입력하세요: "
    ).strip()

    end_year = input(
        "종료 사업연도를 입력하세요: "
    ).strip()

    reprt_code = input(
        "보고서 코드를 입력하세요 "
        "[11011]: "
    ).strip()

    if not reprt_code:
        reprt_code = "11011"

    fs_div = input(
        "재무제표 구분을 입력하세요 "
        "(CFS/OFS) [CFS]: "
    ).strip().upper()

    if not fs_div:
        fs_div = "CFS"

    try:
        result = analyze_company_time_series(
            corporation=corporation,
            start_year=start_year,
            end_year=end_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

    except (
        CompanyTimeSeriesError,
        ValueError,
    ) as error:
        print(
            f"\n기업 시계열 분석 실패: {error}"
        )
        return

    except Exception as error:
        print(
            "\n기업 시계열 분석 중 예상하지 못한 "
            f"오류가 발생했습니다: {error}"
        )
        return

    _print_time_series_result(
        result
    )


def _print_time_series_result(
    result: dict[str, Any],
) -> None:
    print()
    print("[기업 시계열 분석 결과]")
    print("=" * 110)

    stock_code = (
        result.get("stock_code")
        or "비상장"
    )

    print(
        f"기업명: {result['corp_name']} "
        f"({stock_code})"
    )
    print(
        f"고유번호: {result['corp_code']}"
    )
    print(
        f"사업연도: "
        f"{result['start_year']} ~ "
        f"{result['end_year']}"
    )
    print(
        f"보고서 코드: "
        f"{result['reprt_code']}"
    )
    print(
        f"재무제표 구분: "
        f"{result['fs_div']}"
    )

    _print_section(
        title="수익성·안정성 지표",
        columns=BASE_RATIO_COLUMNS,
        rows=result["rows"],
    )

    _print_section(
        title="운전자본 지표",
        columns=WORKING_CAPITAL_COLUMNS,
        rows=result["rows"],
    )

    _print_section(
        title="주요 계정 증감률",
        columns=CHANGE_COLUMNS,
        rows=result["rows"],
    )

    missing_years = result.get(
        "missing_years",
        [],
    )

    if missing_years:
        print()
        print(
            "※ 저장된 분석 결과가 전혀 없는 연도: "
            + ", ".join(missing_years)
        )
        print(
            "  필요한 경우 해당 연도의 prepare를 "
            "먼저 실행하세요."
        )


def _print_section(
    title: str,
    columns: tuple[
        tuple[str, str],
        ...,
    ],
    rows: list[dict[str, Any]],
) -> None:
    year_width = 8
    column_width = 16

    print()
    print(f"[{title}]")
    print(
        "-" * (
            year_width
            + column_width * len(columns)
        )
    )

    print(
        pad(
            "연도",
            year_width,
        ),
        end="",
    )

    for _, column_name in columns:
        print(
            pad(
                column_name,
                column_width,
            ),
            end="",
        )

    print()

    print(
        "-" * (
            year_width
            + column_width * len(columns)
        )
    )

    for row in rows:
        print(
            pad(
                str(row["bsns_year"]),
                year_width,
            ),
            end="",
        )

        for column_code, _ in columns:
            text = _format_value(
                column_code=column_code,
                value=row.get(
                    column_code
                ),
            )

            print(
                pad(
                    text,
                    column_width,
                ),
                end="",
            )

        print()

    print(
        "-" * (
            year_width
            + column_width * len(columns)
        )
    )


def _format_value(
    column_code: str,
    value: Any,
) -> str:
    if value is None:
        return "-"

    format_type = RATIO_FORMATS.get(
        column_code
    )

    if format_type == "turnover":
        return (
            f"{float(value):.2f}회"
        )

    if format_type == "days":
        return (
            f"{float(value):.2f}일"
        )

    return format_ratio(
        value
    )