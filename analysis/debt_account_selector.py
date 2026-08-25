INTEREST_BEARING_DEBT_ACCOUNT_IDS = {
    "ifrs-full_CurrentPortionOfLongtermBorrowings",
    "ifrs-full_NoncurrentPortionOfNoncurrentBondsIssued",
    "ifrs-full_NoncurrentPortionOfNoncurrentLoansReceived",
}

INTEREST_BEARING_DEBT_ACCOUNT_NAMES = {
    "단기차입금",
    "유동성장기부채",
    "유동성장기차입금",
    "유동성사채",
    "장기차입금",
    "사채",
}


def select_interest_bearing_debt_accounts(
    rows: list[dict],
) -> list[dict]:
    """
    재무상태표에서 이자부부채 후보 계정을 선택한다.

    표준 account_id를 우선 사용하고,
    표준계정코드가 없거나 회사별 계정명을 사용하는 경우
    account_nm을 fallback으로 사용한다.
    """
    selected: list[dict] = []
    selected_row_ids: set[int] = set()

    for row in rows:
        account_id = (
            row.get("account_id")
            or ""
        ).strip()

        account_name = (
            row.get("account_nm")
            or ""
        ).strip()

        matched = (
            account_id
            in INTEREST_BEARING_DEBT_ACCOUNT_IDS
            or account_name
            in INTEREST_BEARING_DEBT_ACCOUNT_NAMES
        )

        if not matched:
            continue

        row_id = row.get("id")

        if (
            row_id is not None
            and row_id in selected_row_ids
        ):
            continue

        selected.append(row)

        if row_id is not None:
            selected_row_ids.add(row_id)

    return selected