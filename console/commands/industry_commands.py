from __future__ import annotations

from typing import Any

from database.industry_repository import (
    IndustryRepositoryError,
    add_corporation_to_industry,
    create_industry_group,
    fetch_corporations_by_industry,
    fetch_industry_groups,
    remove_corporation_from_industry,
)
from dart.corporation_service import (
    find_corporations_with_count,
)


def handle_industry_management() -> None:
    """
    산업군 생성·조회 및 산업군별 기업 목록 관리를 수행한다.
    """
    while True:
        print()
        print("[산업군 관리]")
        print("-" * 60)
        print("1. 산업군 생성")
        print("2. 산업군 목록 조회")
        print("3. 산업군에 기업 추가")
        print("4. 산업군 기업 조회")
        print("5. 산업군에서 기업 제거")
        print("0. 이전 메뉴")

        selection = input(
            "선택하세요: "
        ).strip()

        if selection == "1":
            _handle_create_industry_group()

        elif selection == "2":
            _handle_show_industry_groups()

        elif selection == "3":
            _handle_add_industry_members()

        elif selection == "4":
            _handle_show_industry_members()

        elif selection == "5":
            _handle_remove_industry_member()

        elif selection == "0":
            return

        else:
            print("목록에 있는 번호를 입력하세요.")


def _handle_create_industry_group() -> None:
    print()
    print("[산업군 생성]")
    print("-" * 60)

    industry_code = input(
        "산업코드를 입력하세요 "
        "(예: SEMI, SHIP, FIN): "
    ).strip()

    industry_name = input(
        "산업군명을 입력하세요: "
    ).strip()

    description = input(
        "설명을 입력하세요 "
        "(선택, Enter로 생략): "
    ).strip()

    try:
        industry_id = create_industry_group(
            industry_code=industry_code,
            industry_name=industry_name,
            description=description or None,
        )

    except IndustryRepositoryError as error:
        print(f"산업군 생성 실패: {error}")
        return

    except Exception as error:
        print(
            "산업군 생성 중 예상하지 못한 "
            f"오류가 발생했습니다: {error}"
        )
        return

    print()
    print(
        f"산업군이 생성되었습니다: "
        f"{industry_name} "
        f"(industry_id={industry_id})"
    )


def _handle_show_industry_groups() -> None:
    try:
        groups = fetch_industry_groups()

    except IndustryRepositoryError as error:
        print(f"산업군 목록 조회 실패: {error}")
        return

    if not groups:
        print()
        print("저장된 산업군이 없습니다.")
        return

    print()
    print("[산업군 목록]")
    print("-" * 80)

    for index, group in enumerate(
        groups,
        start=1,
    ):
        description = (
            group.get("description")
            or "-"
        )

        print(
            f"{index}. "
            f"{group['industry_name']} "
            f"[{group['industry_code']}] "
            f"/ 기업 수: {group['member_count']:,} "
            f"/ 설명: {description}"
        )


def _handle_add_industry_members() -> None:
    selected_group = _select_industry_group()

    if selected_group is None:
        return

    print()
    print(
        f"[{selected_group['industry_name']}] "
        "산업군에 기업을 추가합니다."
    )
    print(
        "기업명, 종목코드 또는 고유번호를 입력하세요. "
        "종료하려면 stop을 입력하세요."
    )

    while True:
        keyword = input("기업> ").strip()

        if keyword.lower() == "stop":
            break

        if not keyword:
            print("검색어를 입력하세요.")
            continue

        corporation = _select_corporation_by_keyword(
            keyword
        )

        if corporation is None:
            continue

        try:
            added = add_corporation_to_industry(
                industry_id=selected_group[
                    "industry_id"
                ],
                corp_code=corporation["corp_code"],
            )

        except IndustryRepositoryError as error:
            print(
                f"{corporation['corp_name']} 추가 실패: "
                f"{error}"
            )
            continue

        if added:
            print(
                f"추가됨: {corporation['corp_name']} "
                f"({corporation['corp_code']})"
            )
        else:
            print(
                f"{corporation['corp_name']}은(는) "
                "이미 해당 산업군에 등록되어 있습니다."
            )


def _handle_show_industry_members() -> None:
    selected_group = _select_industry_group()

    if selected_group is None:
        return

    try:
        corporations = fetch_corporations_by_industry(
            industry_id=selected_group[
                "industry_id"
            ]
        )

    except IndustryRepositoryError as error:
        print(
            f"산업군 기업 목록 조회 실패: {error}"
        )
        return

    print()
    print(
        f"[{selected_group['industry_name']}] "
        "기업 목록"
    )
    print("-" * 80)

    if not corporations:
        print("등록된 기업이 없습니다.")
        return

    for index, corporation in enumerate(
        corporations,
        start=1,
    ):
        stock_code = (
            corporation.get("stock_code")
            or "비상장"
        )

        print(
            f"{index}. {corporation['corp_name']} "
            f"/ 종목코드: {stock_code} "
            f"/ 고유번호: {corporation['corp_code']}"
        )

    print("-" * 80)
    print(f"총 기업 수: {len(corporations):,}")


def _handle_remove_industry_member() -> None:
    selected_group = _select_industry_group()

    if selected_group is None:
        return

    try:
        corporations = fetch_corporations_by_industry(
            industry_id=selected_group[
                "industry_id"
            ]
        )

    except IndustryRepositoryError as error:
        print(
            f"산업군 기업 목록 조회 실패: {error}"
        )
        return

    if not corporations:
        print("해당 산업군에 등록된 기업이 없습니다.")
        return

    print()
    print(
        f"[{selected_group['industry_name']}] "
        "기업 제거"
    )
    print("-" * 80)

    for index, corporation in enumerate(
        corporations,
        start=1,
    ):
        print(
            f"{index}. {corporation['corp_name']} "
            f"({corporation['corp_code']})"
        )

    selection = input(
        "제거할 기업 번호를 입력하세요 "
        "(취소: Enter): "
    ).strip()

    if not selection:
        return

    try:
        selected_index = int(selection) - 1

    except ValueError:
        print("숫자로 입력해야 합니다.")
        return

    if not 0 <= selected_index < len(corporations):
        print("목록에 있는 번호를 입력하세요.")
        return

    corporation = corporations[selected_index]

    confirm = input(
        f"{corporation['corp_name']}을(를) "
        "산업군에서 제거할까요? [y/N]: "
    ).strip().lower()

    if confirm != "y":
        print("제거를 취소했습니다.")
        return

    try:
        removed = remove_corporation_from_industry(
            industry_id=selected_group[
                "industry_id"
            ],
            corp_code=corporation["corp_code"],
        )

    except IndustryRepositoryError as error:
        print(f"기업 제거 실패: {error}")
        return

    if removed:
        print(
            f"제거됨: {corporation['corp_name']} "
            f"({corporation['corp_code']})"
        )
    else:
        print(
            "해당 기업이 산업군에 등록되어 있지 않습니다."
        )


def _select_industry_group(
) -> dict[str, Any] | None:
    try:
        groups = fetch_industry_groups()

    except IndustryRepositoryError as error:
        print(f"산업군 목록 조회 실패: {error}")
        return None

    if not groups:
        print("저장된 산업군이 없습니다.")
        return None

    print()
    print("[산업군 선택]")
    print("-" * 80)

    for index, group in enumerate(
        groups,
        start=1,
    ):
        print(
            f"{index}. {group['industry_name']} "
            f"[{group['industry_code']}] "
            f"({group['member_count']:,}개 기업)"
        )

    selection = input(
        "산업군 번호를 입력하세요 "
        "(취소: Enter): "
    ).strip()

    if not selection:
        return None

    try:
        selected_index = int(selection) - 1

    except ValueError:
        print("숫자로 입력해야 합니다.")
        return None

    if not 0 <= selected_index < len(groups):
        print("목록에 있는 번호를 입력하세요.")
        return None

    return groups[selected_index]


def _select_corporation_by_keyword(
    keyword: str,
) -> dict[str, Any] | None:
    try:
        result = find_corporations_with_count(
            keyword=keyword,
            limit=20,
        )

    except Exception as error:
        print(
            f"기업 검색 중 오류가 발생했습니다: "
            f"{error}"
        )
        return None

    corporations = result["corporations"]
    total_count = result["total_count"]

    if not corporations:
        print("검색 결과가 없습니다.")
        return None

    if len(corporations) == 1:
        return corporations[0]

    print()
    print("[기업 검색 결과]")
    print("-" * 80)

    for index, corporation in enumerate(
        corporations,
        start=1,
    ):
        stock_code = (
            corporation.get("stock_code")
            or "비상장"
        )

        print(
            f"{index}. {corporation['corp_name']} "
            f"/ 종목코드: {stock_code} "
            f"/ 고유번호: {corporation['corp_code']}"
        )

    if total_count > len(corporations):
        print(
            f"검색 결과 {total_count:,}건 중 "
            f"{len(corporations):,}건만 표시했습니다."
        )

    selection = input(
        "선택할 기업 번호를 입력하세요 "
        "(취소: Enter): "
    ).strip()

    if not selection:
        return None

    try:
        selected_index = int(selection) - 1

    except ValueError:
        print("숫자로 입력해야 합니다.")
        return None

    if not 0 <= selected_index < len(corporations):
        print("목록에 있는 번호를 입력하세요.")
        return None

    return corporations[selected_index]