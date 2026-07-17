from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)


class AccountChangeRatioError(Exception):
    """
    계정별 증감률 조회 또는 계산 과정에서 발생하는 오류.
    """


def _to_decimal(value: Any) -> Decimal | None:
    """
    재무제표 금액을 Decimal로 변환한다.

    다음 값은 None으로 처리한다.

    - None
    - 빈 문자열
    - 숫자로 변환할 수 없는 값
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, int):
        return Decimal(value)

    if isinstance(value, float):
        return Decimal(str(value))

    normalized_value = (
        str(value)
        .strip()
        .replace(",", "")
    )

    if not normalized_value:
        return None

    try:
        return Decimal(normalized_value)

    except InvalidOperation:
        return None


def calculate_account_change_ratio(
    current_amount: Any,
    previous_amount: Any,
) -> dict[str, Decimal | None]:
    """
    당기 금액과 전기 금액을 비교해 증감액과 증감률을 계산한다.

    증감액:
        당기 금액 - 전기 금액

    증감률:
        증감액 / abs(전기 금액) * 100

    전기 금액이 0이면 증감률을 계산할 수 없으므로
    change_ratio는 None을 반환한다.
    """
    current = _to_decimal(current_amount)
    previous = _to_decimal(previous_amount)

    if current is None or previous is None:
        return {
            "change_amount": None,
            "change_ratio": None,
        }

    change_amount = current - previous

    if previous == 0:
        change_ratio = None

    else:
        change_ratio = (
            change_amount
            / abs(previous)
            * Decimal("100")
        )

    return {
        "change_amount": change_amount,
        "change_ratio": change_ratio,
    }


def calculate_account_change_ratios(
    financial_statements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    재무제표의 각 계정에 대해 증감액과 증감률을 계산한다.

    원본 재무제표 행은 수정하지 않고 분석 결과를 담은
    새로운 딕셔너리 목록을 반환한다.
    """
    results: list[dict[str, Any]] = []

    for statement in financial_statements:
        current_amount = _to_decimal(
            statement.get("thstrm_amount")
        )
        previous_amount = _to_decimal(
            statement.get("frmtrm_amount")
        )

        calculation = calculate_account_change_ratio(
            current_amount=current_amount,
            previous_amount=previous_amount,
        )

        results.append(
            {
                "corp_code": statement.get("corp_code"),
                "bsns_year": statement.get("bsns_year"),
                "reprt_code": statement.get("reprt_code"),
                "fs_div": statement.get("fs_div"),
                "fs_nm": statement.get("fs_nm"),
                "sj_div": statement.get("sj_div"),
                "sj_nm": statement.get("sj_nm"),
                "account_id": statement.get("account_id"),
                "account_nm": statement.get("account_nm"),
                "account_detail": statement.get(
                    "account_detail"
                ),
                "current_term_name": statement.get(
                    "thstrm_nm"
                ),
                "previous_term_name": statement.get(
                    "frmtrm_nm"
                ),
                "current_amount": current_amount,
                "previous_amount": previous_amount,
                "change_amount": calculation[
                    "change_amount"
                ],
                "change_ratio": calculation[
                    "change_ratio"
                ],
            }
        )

    return results


def get_account_change_ratios(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
    sj_div: str | None = None,
) -> list[dict[str, Any]]:
    """
    데이터베이스에 저장된 재무제표를 조회한 뒤
    계정별 증감액과 증감률을 계산한다.

    Args:
        corp_code:
            DART 기업 고유번호.

        bsns_year:
            사업연도.

        reprt_code:
            보고서 코드.
            기본값 11011은 사업보고서이다.

        fs_div:
            CFS는 연결재무제표,
            OFS는 별도재무제표이다.

        sj_div:
            BS는 재무상태표,
            IS는 손익계산서,
            CIS는 포괄손익계산서,
            CF는 현금흐름표,
            SCE는 자본변동표이다.

            None이면 모든 재무제표를 조회한다.
    """
    try:
        financial_statements = fetch_financial_statements_from_db(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
            sj_div=sj_div,
        )

    except Exception as error:
        raise AccountChangeRatioError(
            "재무제표 조회 중 오류가 발생했습니다."
        ) from error

    if not financial_statements:
        return []

    return calculate_account_change_ratios(
        financial_statements
    )