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