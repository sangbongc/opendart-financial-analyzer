from typing import Any
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from database.financial_ratio_repository import (
    upsert_financial_ratios,
)
from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)


class FinancialRatioCalculationError(Exception):
    """
    재무비율 계산에 필요한 계정을 찾지 못했거나
    계산할 수 없는 경우 발생한다.
    """

CALCULATION_VERSION = "v2_average_balance"

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
    statements: Iterable[dict],
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    calculation_version: str = CALCULATION_VERSION,
) -> list[dict]:
    """
    재무제표 행을 기반으로 주요 재무비율을 계산한다.

    계산 비율
    ----------
    - 영업이익률
    - 순이익률
    - ROA
    - ROE
    - 부채비율
    - 유동비율

    ROA와 ROE는 당기말과 전기말의 평균잔액을 사용한다.
    """
    statement_rows = list(statements)

    if not statement_rows:
        raise FinancialRatioCalculationError(
            "재무비율 계산에 사용할 재무제표가 없습니다."
        )

    revenue, _ = _extract_account_amounts(
        statements=statement_rows,
        account_key="revenue",
        statement_divisions=("IS", "CIS"),
    )

    operating_profit, _ = _extract_account_amounts(
        statements=statement_rows,
        account_key="operating_profit",
        statement_divisions=("IS", "CIS"),
    )

    net_income, _ = _extract_account_amounts(
        statements=statement_rows,
        account_key="net_income",
        statement_divisions=("IS", "CIS"),
    )

    current_assets_total, previous_assets_total = (
        _extract_account_amounts(
            statements=statement_rows,
            account_key="total_assets",
            statement_divisions=("BS",),
        )
    )

    current_equity_total, previous_equity_total = (
        _extract_account_amounts(
            statements=statement_rows,
            account_key="total_equity",
            statement_divisions=("BS",),
        )
    )

    total_liabilities, _ = _extract_account_amounts(
        statements=statement_rows,
        account_key="total_liabilities",
        statement_divisions=("BS",),
    )

    current_assets, _ = _extract_account_amounts(
        statements=statement_rows,
        account_key="current_assets",
        statement_divisions=("BS",),
    )

    current_liabilities, _ = _extract_account_amounts(
        statements=statement_rows,
        account_key="current_liabilities",
        statement_divisions=("BS",),
    )

    average_assets = _calculate_average(
        current_value=current_assets_total,
        previous_value=previous_assets_total,
    )

    average_equity = _calculate_average(
        current_value=current_equity_total,
        previous_value=previous_equity_total,
    )

    ratios = [
        {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
            "ratio_code": "OPERATING_MARGIN",
            "ratio_name": "영업이익률",
            "ratio_value": _calculate_percentage(
                numerator=operating_profit,
                denominator=revenue,
            ),
            "numerator_value": _to_storage_number(
                operating_profit
            ),
            "denominator_value": _to_storage_number(
                revenue
            ),
            "calculation_version": calculation_version,
        },
        {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
            "ratio_code": "NET_PROFIT_MARGIN",
            "ratio_name": "순이익률",
            "ratio_value": _calculate_percentage(
                numerator=net_income,
                denominator=revenue,
            ),
            "numerator_value": _to_storage_number(
                net_income
            ),
            "denominator_value": _to_storage_number(
                revenue
            ),
            "calculation_version": calculation_version,
        },
        {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
            "ratio_code": "ROA",
            "ratio_name": "총자산이익률",
            "ratio_value": _calculate_percentage(
                numerator=net_income,
                denominator=average_assets,
            ),
            "numerator_value": _to_storage_number(
                net_income
            ),
            "denominator_value": _to_storage_number(
                average_assets
            ),
            "calculation_version": calculation_version,
        },
        {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
            "ratio_code": "ROE",
            "ratio_name": "자기자본이익률",
            "ratio_value": _calculate_percentage(
                numerator=net_income,
                denominator=average_equity,
            ),
            "numerator_value": _to_storage_number(
                net_income
            ),
            "denominator_value": _to_storage_number(
                average_equity
            ),
            "calculation_version": calculation_version,
        },
        {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
            "ratio_code": "DEBT_RATIO",
            "ratio_name": "부채비율",
            "ratio_value": _calculate_percentage(
                numerator=total_liabilities,
                denominator=current_equity_total,
            ),
            "numerator_value": _to_storage_number(
                total_liabilities
            ),
            "denominator_value": _to_storage_number(
                current_equity_total
            ),
            "calculation_version": calculation_version,
        },
        {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
            "ratio_code": "CURRENT_RATIO",
            "ratio_name": "유동비율",
            "ratio_value": _calculate_percentage(
                numerator=current_assets,
                denominator=current_liabilities,
            ),
            "numerator_value": _to_storage_number(
                current_assets
            ),
            "denominator_value": _to_storage_number(
                current_liabilities
            ),
            "calculation_version": calculation_version,
        },
    ]

    return ratios

def calculate_and_save_financial_ratios(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
    calculation_version: str = CALCULATION_VERSION,
) -> dict:
    """
    저장된 재무제표를 조회하여 재무비율을 계산하고 저장한다.
    """
    statements = fetch_financial_statements_from_db(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
    )

    if not statements:
        raise FinancialRatioCalculationError(
            "조건에 해당하는 재무제표가 저장되어 있지 않습니다. "
            f"corp_code={corp_code}, "
            f"bsns_year={bsns_year}, "
            f"reprt_code={reprt_code}, "
            f"fs_div={fs_div}"
        )

    ratios = calculate_financial_ratios(
        statements=statements,
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
        calculation_version=calculation_version,
    )

    saved_count = upsert_financial_ratios(ratios)

    unavailable_ratios = [
        ratio["ratio_code"]
        for ratio in ratios
        if ratio["ratio_value"] is None
    ]

    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "calculation_version": calculation_version,
        "calculated_count": len(ratios),
        "saved_count": saved_count,
        "unavailable_ratios": unavailable_ratios,
        "ratios": ratios,
    }
def _normalize_account_name(
    account_name: str | None,
) -> str:
    """
    계정과목 비교를 위해 공백을 제거한다.
    """
    if account_name is None:
        return ""

    return "".join(account_name.split())


def _parse_amount(
    value: Any,
) -> Decimal | None:
    """
    DART 재무제표 금액을 Decimal로 변환한다.

    다음 값은 None으로 처리한다.

    - None
    - 빈 문자열
    - "-"
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, int | float):
        return Decimal(str(value))

    text = str(value).strip()

    if not text or text == "-":
        return None

    text = text.replace(",", "")

    # 일부 재무자료에서 괄호가 음수를 의미할 수 있다.
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"

    try:
        return Decimal(text)

    except InvalidOperation:
        return None


def _find_account_row(
    statements: Iterable[dict],
    aliases: tuple[str, ...],
    statement_divisions: tuple[str, ...] | None = None,
) -> dict | None:
    """
    계정과목 별칭과 일치하는 재무제표 행을 찾는다.

    statement_divisions를 전달하면 해당 재무제표 구분에서만 찾는다.

    예:
    - BS: 재무상태표
    - IS: 손익계산서
    - CIS: 포괄손익계산서
    """
    normalized_aliases = {
        _normalize_account_name(alias)
        for alias in aliases
    }

    candidates: list[dict] = []

    for row in statements:
        if statement_divisions is not None:
            if row.get("sj_div") not in statement_divisions:
                continue

        account_name = _normalize_account_name(
            row.get("account_nm")
        )

        if account_name in normalized_aliases:
            candidates.append(row)

    if not candidates:
        return None

    # account_detail이 없는 기본 계정 행을 우선한다.
    candidates.sort(
        key=lambda row: (
            bool(str(row.get("account_detail") or "").strip()),
            str(row.get("account_id") or ""),
        )
    )

    return candidates[0]


def _extract_account_amounts(
    statements: list[dict],
    account_key: str,
    statement_divisions: tuple[str, ...] | None = None,
) -> tuple[Decimal | None, Decimal | None]:
    """
    특정 계정과목의 당기 금액과 전기 금액을 반환한다.

    Returns
    -------
    tuple
        (당기 금액, 전기 금액)
    """
    aliases = ACCOUNT_ALIASES[account_key]

    row = _find_account_row(
        statements=statements,
        aliases=aliases,
        statement_divisions=statement_divisions,
    )

    if row is None:
        return None, None

    current_amount = _parse_amount(
        row.get("thstrm_amount")
    )

    previous_amount = _parse_amount(
        row.get("frmtrm_amount")
    )

    return current_amount, previous_amount


def _calculate_percentage(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> float | None:
    """
    분자와 분모를 받아 백분율을 계산한다.

    계산할 수 없거나 분모가 0이면 None을 반환한다.
    """
    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    result = numerator / denominator * Decimal("100")

    return float(result)


def _calculate_average(
    current_value: Decimal | None,
    previous_value: Decimal | None,
) -> Decimal | None:
    """
    당기와 전기의 평균잔액을 계산한다.

    두 금액 중 하나라도 없으면 None을 반환한다.
    당기말 잔액으로 대체 계산하지 않는다.
    """
    if current_value is None or previous_value is None:
        return None

    return (
        current_value + previous_value
    ) / Decimal("2")


def _to_storage_number(
    value: Decimal | None,
) -> int | float | None:
    """
    Decimal 값을 SQLite 저장에 적합한 숫자로 변환한다.
    """
    if value is None:
        return None

    if value == value.to_integral_value():
        return int(value)

    return float(value)