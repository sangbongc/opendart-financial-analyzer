from typing import Any


class FinancialRatioCalculationError(Exception):
    """
    재무비율 계산에 필요한 계정을 찾지 못했거나
    계산할 수 없는 경우 발생한다.
    """


ACCOUNT_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": (
        "매출액",
        "수익(매출액)",
        "영업수익",
        "수익",
    ),
    "operating_profit": (
        "영업이익",
        "영업이익(손실)",
        "영업손익",
    ),
    "net_income": (
        "당기순이익",
        "당기순이익(손실)",
        "당기순손익",
        "연결당기순이익",
    ),
    "total_assets": (
        "자산총계",
        "자산총액",
    ),
    "total_liabilities": (
        "부채총계",
        "부채총액",
    ),
    "total_equity": (
        "자본총계",
        "자본총액",
    ),
    "current_assets": (
        "유동자산",
    ),
    "current_liabilities": (
        "유동부채",
    ),
}


STATEMENT_PRIORITY: dict[str, tuple[str, ...]] = {
    "revenue": (
        "IS",
        "CIS",
    ),
    "operating_profit": (
        "IS",
        "CIS",
    ),
    "net_income": (
        "IS",
        "CIS",
    ),
    "total_assets": (
        "BS",
    ),
    "total_liabilities": (
        "BS",
    ),
    "total_equity": (
        "BS",
    ),
    "current_assets": (
        "BS",
    ),
    "current_liabilities": (
        "BS",
    ),
}


def _parse_amount(value: object) -> int | None:
    """
    DB에서 조회한 금액을 정수로 변환한다.

    None, 빈 문자열, '-'는 값이 없는 것으로 처리한다.
    쉼표가 포함된 문자열도 처리한다.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    text = str(value).strip()

    if not text or text == "-":
        return None

    text = text.replace(",", "")

    try:
        return int(text)
    except ValueError as error:
        raise FinancialRatioCalculationError(
            f"금액을 숫자로 변환할 수 없습니다: {value}"
        ) from error


def _find_account_row(
    rows: list[dict[str, Any]],
    account_key: str,
) -> dict[str, Any] | None:
    """
    계정 별칭과 재무제표 우선순위를 기준으로
    가장 적합한 재무제표 행을 찾는다.
    """
    aliases = ACCOUNT_ALIASES[account_key]
    statement_priority = STATEMENT_PRIORITY[account_key]

    for statement_code in statement_priority:
        for alias in aliases:
            for row in rows:
                if row.get("sj_div") != statement_code:
                    continue

                if row.get("account_nm") == alias:
                    return row

    return None


def _get_account_amount(
    rows: list[dict[str, Any]],
    account_key: str,
    amount_field: str = "thstrm_amount",
    required: bool = True,
) -> int | None:
    """
    지정한 계정의 금액을 반환한다.
    """
    row = _find_account_row(
        rows=rows,
        account_key=account_key,
    )

    if row is None:
        if required:
            aliases = ", ".join(
                ACCOUNT_ALIASES[account_key]
            )

            raise FinancialRatioCalculationError(
                "필요한 계정을 찾지 못했습니다. "
                f"계정 후보: {aliases}"
            )

        return None

    amount = _parse_amount(
        row.get(amount_field)
    )

    if amount is None and required:
        raise FinancialRatioCalculationError(
            f"{row['account_nm']}의 "
            f"{amount_field} 값이 없습니다."
        )

    return amount


def _calculate_percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """
    분모가 0이면 None을 반환하고,
    그 외에는 백분율을 계산한다.
    """
    if denominator == 0:
        return None

    return numerator / denominator * 100


def _calculate_average(
    current_amount: int,
    previous_amount: int | None,
) -> float:
    """
    전기 금액이 있으면 당기·전기 평균을 계산한다.

    전기 금액이 없으면 당기 금액을 사용한다.
    """
    if previous_amount is None:
        return float(current_amount)

    return (
        current_amount + previous_amount
    ) / 2


def calculate_financial_ratios(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    조회된 재무제표 원본 행으로 주요 재무비율을 계산한다.

    반환 비율의 단위는 백분율(%)이다.
    """
    if not rows:
        raise FinancialRatioCalculationError(
            "재무비율을 계산할 재무제표가 없습니다."
        )

    revenue = _get_account_amount(
        rows,
        "revenue",
    )
    operating_profit = _get_account_amount(
        rows,
        "operating_profit",
    )
    net_income = _get_account_amount(
        rows,
        "net_income",
    )
    total_assets = _get_account_amount(
        rows,
        "total_assets",
    )
    total_liabilities = _get_account_amount(
        rows,
        "total_liabilities",
    )
    total_equity = _get_account_amount(
        rows,
        "total_equity",
    )
    current_assets = _get_account_amount(
        rows,
        "current_assets",
    )
    current_liabilities = _get_account_amount(
        rows,
        "current_liabilities",
    )

    previous_assets = _get_account_amount(
        rows,
        "total_assets",
        amount_field="frmtrm_amount",
        required=False,
    )
    previous_equity = _get_account_amount(
        rows,
        "total_equity",
        amount_field="frmtrm_amount",
        required=False,
    )

    average_assets = _calculate_average(
        current_amount=total_assets,
        previous_amount=previous_assets,
    )
    average_equity = _calculate_average(
        current_amount=total_equity,
        previous_amount=previous_equity,
    )

    return {
        "source": {
            "corp_code": rows[0].get("corp_code"),
            "bsns_year": rows[0].get("bsns_year"),
            "reprt_code": rows[0].get("reprt_code"),
            "fs_div": rows[0].get("fs_div"),
        },
        "accounts": {
            "revenue": revenue,
            "operating_profit": operating_profit,
            "net_income": net_income,
            "total_assets": total_assets,
            "previous_assets": previous_assets,
            "average_assets": average_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "previous_equity": previous_equity,
            "average_equity": average_equity,
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
        },
        "ratios": {
            "operating_margin": _calculate_percentage(
                operating_profit,
                revenue,
            ),
            "net_profit_margin": _calculate_percentage(
                net_income,
                revenue,
            ),
            "roa": _calculate_percentage(
                net_income,
                average_assets,
            ),
            "roe": _calculate_percentage(
                net_income,
                average_equity,
            ),
            "debt_ratio": _calculate_percentage(
                total_liabilities,
                total_equity,
            ),
            "current_ratio": _calculate_percentage(
                current_assets,
                current_liabilities,
            ),
        },
    }