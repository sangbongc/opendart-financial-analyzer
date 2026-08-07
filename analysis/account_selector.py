from __future__ import annotations

import re
from typing import Any


CURRENT_MARKERS: tuple[str, ...] = (
    "current",
    "유동",
    "단기",
)

NONCURRENT_MARKERS: tuple[str, ...] = (
    "noncurrent",
    "non-current",
    "비유동",
    "장기",
)


ACCOUNT_HEADING_PREFIX = re.compile(
    r"^\s*(?:"
    r"[IVXLCDM]+[.)]"
    r"|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+[.)]"
    r"|\d+[.)]"
    r"|\(\d+\)"
    r"|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]"
    r"|[가-하][.)]"
    r")\s*"
)


def normalize_account_name(
    account_name: Any,
) -> str:
    """
    계정명 비교를 위해 앞쪽 목차 표기와 공백을 제거한다.

    예: ``I. 유형자산`` -> ``유형자산``
        ``Ⅱ. 매출채권`` -> ``매출채권``
        ``(1) 재고자산`` -> ``재고자산``

    문자열 중간/뒤의 괄호나 숫자는 계정 의미일 수 있으므로
    제거하지 않는다.
    """
    text = str(account_name or "").strip()

    if not text:
        return ""

    text = ACCOUNT_HEADING_PREFIX.sub("", text, count=1)

    return "".join(text.split())


def account_scope_priority(
    row: dict[str, Any],
    *,
    prefer_current: bool = True,
) -> int:
    """
    계정 후보가 유동/비유동으로 중복될 때 우선순위를 반환한다.

    낮을수록 우선한다.

    prefer_current=True:
        유동(0) -> 구분 불명(1) -> 비유동(2)

    prefer_current=False:
        비유동(0) -> 구분 불명(1) -> 유동(2)

    account_id를 가장 중요한 판단 근거로 보고,
    account_nm / account_detail도 보조적으로 확인한다.
    """
    texts = (
        str(row.get("account_id") or ""),
        str(row.get("account_nm") or ""),
        str(row.get("account_detail") or ""),
    )

    normalized = " ".join(texts).lower().replace("_", " ")

    # '비유동' 안에 '유동'이 포함되므로 비유동을 먼저 판정한다.
    is_noncurrent = any(
        marker in normalized
        for marker in NONCURRENT_MARKERS
    )
    is_current = (
        not is_noncurrent
        and any(
            marker in normalized
            for marker in CURRENT_MARKERS
        )
    )

    if prefer_current:
        if is_current:
            return 0
        if is_noncurrent:
            return 2
        return 1

    if is_noncurrent:
        return 0
    if is_current:
        return 2
    return 1


def select_preferred_account_row(
    rows: list[dict[str, Any]],
    *,
    prefer_current: bool = True,
) -> dict[str, Any] | None:
    """유동/비유동 구분을 고려해 가장 적절한 계정 후보를 고른다."""
    if not rows:
        return None

    return min(
        rows,
        key=lambda row: (
            account_scope_priority(
                row,
                prefer_current=prefer_current,
            ),
            int(
                bool(
                    str(row.get("account_detail") or "").strip()
                )
            ),
        ),
    )