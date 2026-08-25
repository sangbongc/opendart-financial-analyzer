from pprint import pprint

from analysis.capital_structure_service import (
    get_capital_structure,
    get_interest_bearing_debt,
)
from analysis.capital_structure_service import (
    get_capital_structure_analysis,
)


CORP_CODE = "00126380"  # 삼성전자
BSNS_YEAR = "2025"
REPRT_CODE = "11011"
FS_DIV = "CFS"


def main() -> None:
    print("\n[자본구조 분석 Smoke Test]")
    print("-" * 80)

    capital_structure = get_capital_structure(
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
    )

    print("\n[1. 회계상 자본구조]")
    pprint(capital_structure)

    print("\n부채총계:")
    print(
        f"{capital_structure['total_liabilities']:,}원"
    )

    print("\n자본총계:")
    print(
        f"{capital_structure['total_equity']:,}원"
    )

    print("\n회계상 D/E:")
    print(
        f"{capital_structure['accounting_debt_to_equity']:.4f}"
    )

    print("\n" + "-" * 80)

    debt_result = get_interest_bearing_debt(
        corp_code=CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE,
        fs_div=FS_DIV,
    )

    print("\n[2. 이자부부채]")
    pprint(debt_result)

    print("\n이자부부채 계정:")
    for account in debt_result["debt_accounts"]:
        print(
            f"- {account['account_nm']} "
            f"({account['account_id']}): "
            f"{account['amount']:,}원"
        )

    print("\n이자부부채 총액:")
    print(
        f"{debt_result['interest_bearing_debt']:,}원"
    )

    expected_debt = 25_239_139_000_000

    print("\n[3. 합산 검증]")
    print(
        f"예상값: {expected_debt:,}원"
    )
    print(
        "결과:",
        (
            "PASS"
            if debt_result["interest_bearing_debt"]
            == expected_debt
            else "FAIL"
        ),
    )


if __name__ == "__main__":
    main()
    result = get_capital_structure_analysis(
    corp_code="00126380",
    bsns_year="2025",
    reprt_code="11011",
    fs_div="CFS",
)

    print("\n[종합 자본구조 분석]")
    print(
        "회계상 D/E:",
        f"{result['accounting_debt_to_equity']:.2%}",
    )
    print(
        "이자부부채 D/E:",
        f"{result['interest_bearing_debt_to_equity']:.2%}",
    )
    print(
        "총부채 중 이자부부채 비중:",
        f"{result['interest_bearing_debt_ratio']:.2%}",
    )