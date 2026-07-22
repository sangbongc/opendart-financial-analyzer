


def get_qname_local_name(
    value: str,
) -> str:
    """
    QName 문자열에서 prefix를 제외한 local name을 반환한다.

    예:
    ifrs-full:ConsolidatedMember
        -> ConsolidatedMember
    """
    if ":" not in value:
        return value

    return value.split(":", 1)[-1]