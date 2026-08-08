from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


from analysis.finance_company_analysis.bank_company_comparison_service import (
    BankCompanyComparisonError,
    compare_bank_companies,
    format_bank_comparison_table,
    format_bank_rankings,
)


BANKS = (
    {
        "corp_name": "KB금융",
        "corp_code": "00688996",
    },
    {
        "corp_name": "신한지주",
        "corp_code": "00382199",
    },
    {
        "corp_name": "하나금융지주",
        "corp_code": "00547583",
    },
    {
        "corp_name": "우리금융지주",
        "corp_code": "01350869",
    },
    {
        "corp_name": "농협금융지주",
        "corp_code": "00908021",
    },
)


def run_smoke_test(
    *,
    bsns_year: str = "2025",
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> None:
    """
    실제 SQLite DB에 저장된 5개 금융지주 재무제표를 이용하여
    금융회사 비교 서비스 전체 흐름을 검증한다.

    비교 결과는 DB에 저장하지 않는다.
    """
    print()
    print("=" * 130)
    print("[은행·금융지주 비교 Smoke Test]")
    print("=" * 130)
    print(f"사업연도: {bsns_year}")
    print(f"보고서 코드: {reprt_code}")
    print(f"재무제표 구분: {fs_div}")
    print(
        "비교 기업: "
        + ", ".join(
            bank["corp_name"]
            for bank in BANKS
        )
    )

    try:
        comparison = compare_bank_companies(
            BANKS,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )
    except BankCompanyComparisonError as error:
        print()
        print(f"비교 실패: {error}")
        return
    except Exception as error:
        print()
        print(
            "비교 중 예상하지 못한 오류가 발생했습니다: "
            f"{error}"
        )
        raise

    print()
    print("[1. 기업별 재무비율 비교]")
    print()
    print(
        format_bank_comparison_table(
            comparison
        )
    )

    print()
    print("[2. 비율별 수치 순위]")
    print()
    print(
        format_bank_rankings(
            comparison
        )
    )

    print()
    print("[3. Smoke Test 결과 요약]")
    print("-" * 80)

    company_count = comparison.get(
        "company_count",
        0,
    )
    unavailable_companies = comparison.get(
        "unavailable_companies",
        [],
    )

    print(f"비교 요청 기업 수: {len(BANKS)}")
    print(f"비교 성공 기업 수: {company_count}")
    print(
        "비교 제외 기업 수: "
        f"{len(unavailable_companies)}"
    )

    expected_ratio_count = 8

    incomplete_companies = []

    for company in comparison.get(
        "companies",
        [],
    ):
        ratios = company.get("ratios", {})

        available_ratio_count = sum(
            1
            for ratio in ratios.values()
            if ratio.get("ratio_value") is not None
        )

        print(
            f"- {company['corp_name']}: "
            f"{available_ratio_count}/"
            f"{expected_ratio_count} 계산"
        )

        if (
            available_ratio_count
            != expected_ratio_count
        ):
            missing_codes = [
                code
                for code, ratio in ratios.items()
                if ratio.get("ratio_value") is None
            ]

            incomplete_companies.append(
                {
                    "corp_name": company["corp_name"],
                    "available_ratio_count": (
                        available_ratio_count
                    ),
                    "missing_codes": missing_codes,
                }
            )

    if unavailable_companies:
        print()
        print("[비교 제외 상세]")

        for row in unavailable_companies:
            print(
                f"- {row['corp_name']} "
                f"({row['corp_code']}): "
                f"{row['reason']}"
            )

    if incomplete_companies:
        print()
        print("[계산 불완전 기업]")

        for row in incomplete_companies:
            missing_text = ", ".join(
                row["missing_codes"]
            ) or "확인 필요"

            print(
                f"- {row['corp_name']}: "
                f"{row['available_ratio_count']}/"
                f"{expected_ratio_count}, "
                f"미계산={missing_text}"
            )

    print()
    if (
        company_count == len(BANKS)
        and not unavailable_companies
        and not incomplete_companies
    ):
        print(
            "PASS: 5개 금융지주 모두 "
            "8개 재무비율 비교가 정상 수행되었습니다."
        )
    else:
        print(
            "CHECK: 일부 기업 또는 비율을 "
            "추가 확인해야 합니다."
        )


def main() -> None:
    run_smoke_test(
        bsns_year="2025",
        reprt_code="11011",
        fs_div="CFS",
    )


if __name__ == "__main__":
    main()