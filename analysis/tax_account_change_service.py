from typing import Any

from analysis.account_change_ratio_service import (
    get_account_change_ratios,
)




TAX_ACCOUNT_GROUPS = {
    "deferred_tax_asset": {
        "display_name": "이연법인세자산",
        "statement_division": "BS",
        "account_names": (
            "이연법인세자산",
            "비유동이연법인세자산",
        ),
    },
    "deferred_tax_liability": {
        "display_name": "이연법인세부채",
        "statement_division": "BS",
        "account_names": (
            "이연법인세부채",
            "비유동이연법인세부채",
        ),
    },
    "current_tax_asset": {
        "display_name": "당기법인세자산",
        "statement_division": "BS",
        "account_names": (
            "당기법인세자산",
            "미수법인세",
        ),
    },
    "current_tax_liability": {
        "display_name": "당기법인세부채",
        "statement_division": "BS",
        "account_names": (
            "당기법인세부채",
            "미지급법인세",
        ),
    },
}


def get_tax_account_changes(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> list[dict[str, Any]]:
    """
    저장된 재무제표의 계정별 변동 내역 중 세무 관련 계정만 반환한다.

    반환 결과에는 다음 정보가 포함된다.

    - 실제 재무제표 계정명
    - 세무 계정 분류 코드
    - 표준화된 세무 계정명
    - 당기 금액
    - 전기 금액
    - 증감액
    - 증감률

    결과는 증감액 절댓값이 큰 순서로 정렬한다.
    """
    account_changes = get_account_change_ratios(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
        sj_div="BS",
    )

    results: list[dict[str, Any]] = []

    for row in account_changes:
        account_name = str(
            row.get("account_nm") or ""
        ).strip()

        tax_account_info = TAX_ACCOUNT_LOOKUP.get(
            account_name
        )

        if tax_account_info is None:
            continue

        results.append(
            {
                **row,
                "tax_account_code": (
                    tax_account_info["tax_account_code"]
                ),
                "tax_account_name": (
                    tax_account_info["tax_account_name"]
                ),
            }
        )

    results.sort(
        key=lambda row: abs(
            _get_change_amount(row)
        ),
        reverse=True,
    )

    return results


def _get_change_amount(
    row: dict[str, Any],
) -> int | float:
    """
    계정별 증감률 서비스의 결과에서 증감액을 가져온다.

    change_amount가 없으면 당기 금액과 전기 금액으로 다시 계산한다.
    """
    change_amount = row.get("change_amount")

    if isinstance(change_amount, (int, float)):
        return change_amount

    current_amount = _to_number(
        row.get("current_amount")
    )
    previous_amount = _to_number(
        row.get("previous_amount")
    )

    return current_amount - previous_amount


def _to_number(value: Any) -> int | float:
    """
    숫자 또는 숫자형 문자열을 계산 가능한 값으로 변환한다.
    """
    if value is None:
        return 0

    if isinstance(value, (int, float)):
        return value

    try:
        return int(
            str(value).replace(",", "").strip()
        )
    except (TypeError, ValueError):
        return 0


def _build_tax_account_lookup() -> dict[str, dict[str, str]]:
    """
    실제 재무제표 계정명을 세무 계정 분류 정보에 연결한다.

    예:
    {
        "비유동이연법인세자산": {
            "tax_account_code": "deferred_tax_asset",
            "tax_account_name": "이연법인세자산",
            "sj_div": "BS",
        }
    }
    """
    lookup: dict[str, dict[str, str]] = {}

    for account_code, group in TAX_ACCOUNT_GROUPS.items():
        display_name = str(group["display_name"])
        sj_div = str(group["statement_division"])

        for account_name in group["account_names"]:
            lookup[str(account_name)] = {
                "tax_account_code": account_code,
                "tax_account_name": display_name,
                "sj_div": sj_div,
            }

    return lookup



TAX_ACCOUNT_LOOKUP = _build_tax_account_lookup()
