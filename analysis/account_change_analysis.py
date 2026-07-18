from typing import Any


SIGNIFICANT_CHANGE_THRESHOLD = 20.0


MAJOR_ACCOUNT_RULES = {
    "매출액": {
        "aliases": (
            "매출액",
            "영업수익",
            "수익(매출액)",
        ),
        "message": (
            "매출 규모에 유의적인 변동이 발생했습니다. "
            "사업 부문별 매출과 영업환경의 변화를 추가로 확인할 필요가 있습니다."
        ),
    },
    "영업이익": {
        "aliases": (
            "영업이익",
            "영업이익(손실)",
        ),
        "message": (
            "영업성과에 유의적인 변동이 발생했습니다. "
            "매출과 주요 비용 항목의 변동을 함께 검토할 필요가 있습니다."
        ),
    },
    "당기순이익": {
        "aliases": (
            "당기순이익",
            "당기순이익(손실)",
            "연결당기순이익",
        ),
        "message": (
            "당기순이익에 유의적인 변동이 발생했습니다. "
            "영업손익과 영업외손익, 법인세비용의 영향을 확인할 필요가 있습니다."
        ),
    },
    "자산총계": {
        "aliases": (
            "자산총계",
        ),
        "message": (
            "총자산 규모에 유의적인 변동이 발생했습니다. "
            "변동에 영향을 준 주요 자산 항목을 확인할 필요가 있습니다."
        ),
    },
    "부채총계": {
        "aliases": (
            "부채총계",
        ),
        "message": (
            "총부채 규모에 유의적인 변동이 발생했습니다. "
            "차입금과 영업 관련 부채의 변화를 확인할 필요가 있습니다."
        ),
    },
    "자본총계": {
        "aliases": (
            "자본총계",
        ),
        "message": (
            "자본 규모에 유의적인 변동이 발생했습니다. "
            "당기손익, 배당 및 자본거래의 영향을 확인할 필요가 있습니다."
        ),
    },
    "재고자산": {
        "aliases": (
            "재고자산",
        ),
        "message": (
            "재고자산에 유의적인 변동이 발생했습니다. "
            "재고 구성과 판매 추이, 평가손실 발생 여부를 확인할 필요가 있습니다."
        ),
    },
    "매출채권": {
        "aliases": (
            "매출채권",
            "매출채권 및 기타채권",
            "매출채권및기타채권",
        ),
        "message": (
            "매출채권에 유의적인 변동이 발생했습니다. "
            "매출 변화와 채권 회수 현황을 함께 확인할 필요가 있습니다."
        ),
    },
}

def _find_rule(account_name: str) -> tuple[str, dict[str, Any]] | None:
    normalized_name = account_name.replace(" ", "")

    for major_name, rule in MAJOR_ACCOUNT_RULES.items():
        aliases = rule["aliases"]

        for alias in aliases:
            normalized_alias = alias.replace(" ", "")

            if normalized_name == normalized_alias:
                return major_name, rule

    return None


def analyze_major_account_changes(
    results: list[dict[str, Any]],
    threshold: float = SIGNIFICANT_CHANGE_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    계정별 증감률 계산 결과 중 주요 계정을 선별하고,
    일정 기준 이상의 변동이 발생한 계정에 분석 문구를 생성한다.
    """
    analyses: list[dict[str, Any]] = []

    for result in results:
        account_name = str(result.get("account_nm") or "")
        change_ratio = result.get("change_ratio")

        if not account_name:
            continue

        if change_ratio is None:
            continue

        matched_rule = _find_rule(account_name)

        if matched_rule is None:
            continue

        major_name, rule = matched_rule

        try:
            numeric_ratio = float(change_ratio)
        except (TypeError, ValueError):
            continue

        if abs(numeric_ratio) < threshold:
            continue

        direction = "증가" if numeric_ratio > 0 else "감소"

        analyses.append(
            {
                "account_nm": account_name,
                "major_account_nm": major_name,
                "change_ratio": numeric_ratio,
                "direction": direction,
                "message": rule["message"],
            }
        )

    return analyses

def print_major_account_analyses(
    analyses: list[dict[str, Any]],
) -> None:
    print("\n[주요 계정 변동 분석]")
    print("-" * 60)

    if not analyses:
        print("설정된 기준을 초과한 주요 계정 변동이 없습니다.")
        return

    for analysis in analyses:
        account_name = analysis["account_nm"]
        change_ratio = analysis["change_ratio"]
        direction = analysis["direction"]
        message = analysis["message"]

        print(
            f"- {account_name}: "
            f"{abs(change_ratio):,.2f}% {direction}"
        )
        print(f"  {message}")

def _normalize_account_name(account_name: str) -> str:
    return (
        account_name
        .replace(" ", "")
        .replace("(손실)", "")
    )


def _find_account_result(
    results: list[dict[str, Any]],
    aliases: tuple[str, ...],
) -> dict[str, Any] | None:
    normalized_aliases = {
        _normalize_account_name(alias)
        for alias in aliases
    }

    for result in results:
        account_name = str(
            result.get("account_nm") or ""
        )

        normalized_name = _normalize_account_name(
            account_name
        )

        if normalized_name in normalized_aliases:
            return result

    return None

def analyze_inventory_vs_revenue(
    results: list[dict[str, Any]],
    difference_threshold: float = 10.0,
) -> dict[str, Any] | None:
    """
    기본 임계값은 10%p를 기준으로 한다
    """
    revenue = _find_account_result(
        results,
        (
            "매출액",
            "수익(매출액)",
            "영업수익",
        ),
    )

    inventory = _find_account_result(
        results,
        (
            "재고자산",
        ),
    )

    if revenue is None or inventory is None:
        return None

    revenue_ratio = revenue.get("change_ratio")
    inventory_ratio = inventory.get("change_ratio")

    if revenue_ratio is None or inventory_ratio is None:
        return None

    try:
        revenue_ratio = float(revenue_ratio)
        inventory_ratio = float(inventory_ratio)
    except (TypeError, ValueError):
        return None

    difference = inventory_ratio - revenue_ratio

    if difference < difference_threshold:
        return None

    return {
        "title": "재고자산과 매출액 변동 비교",
        "message": (
            f"재고자산 증가율({inventory_ratio:,.2f}%)이 "
            f"매출액 증가율({revenue_ratio:,.2f}%)보다 "
            f"{difference:,.2f}%p 높습니다. "
            "재고 구성, 판매 추이 및 재고평가 관련 사항을 "
            "추가로 확인할 필요가 있습니다."
        ),
    }

def print_inventory_vs_revenue_analysis(
    analysis: dict[str, Any] | None,
) -> None:
    print("\n[매출액과 재고자산 변동 비교]")
    print("-" * 60)

    if analysis is None:
        print(
            "비교 기준을 충족하는 매출액과 "
            "재고자산 변동이 없습니다."
        )
        return

    print(analysis["message"])