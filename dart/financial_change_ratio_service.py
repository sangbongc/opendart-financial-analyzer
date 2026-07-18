from utils import (
    format_amount,
    format_ratio,
    pad_right,
    pad,
)
from wcwidth import wcswidth

def print_account_change_ratios(
    results: list[dict],
) -> None:
    """
    계정별 증감률 계산 결과를 콘솔에 출력한다.
    """
    if not results:
        print("조회된 계정 증감률 데이터가 없습니다.")
        return

    formatted_rows = []

    for row in results:
        formatted_rows.append(
            {
                "account_name": row.get("account_nm") or "-",
                "current_amount": format_amount(
                    row.get("current_amount")
                ),
                "previous_amount": format_amount(
                    row.get("previous_amount")
                ),
                "change_amount": format_amount(
                    row.get("change_amount")
                ),
                "change_ratio": format_ratio(
                    row.get("change_ratio")
                ),
            }
        )

    name_width = max(
        28,
        max(
            wcswidth(row["account_name"])
            for row in formatted_rows
        ) + 2,
    )

    amount_width = max(
        20,
        max(
            wcswidth(value)
            for row in formatted_rows
            for value in (
                row["current_amount"],
                row["previous_amount"],
                row["change_amount"],
            )
        ) + 3,
    )

    ratio_width = max(
        10,
        max(
            wcswidth(row["change_ratio"])
            for row in formatted_rows
        ) + 3,
    )

    total_width = (
        name_width
        + amount_width * 3
        + ratio_width
    )

    print()
    print("[계정별 증감 분석]")
    print("-" * total_width)

    print(
        pad("계정명", name_width)
        + pad_right("당기 금액", amount_width)
        + pad_right("전기 금액", amount_width)
        + pad_right("증감액", amount_width)
        + pad_right("증감률", ratio_width)
    )

    print("-" * total_width)

    for row in formatted_rows:
        print(
            pad(row["account_name"], name_width)
            + pad_right(row["current_amount"], amount_width)
            + pad_right(row["previous_amount"], amount_width)
            + pad_right(row["change_amount"], amount_width)
            + pad_right(row["change_ratio"], ratio_width)
        )

    print("-" * total_width)
    print(f"총 계정 수: {len(results):,}개")
