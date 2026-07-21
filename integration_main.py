from analysis.xbrl_note_table_parser import (
    parse_note_table_line_items,
    _get_concept_id_from_href,
    _get_presentation_file_name,
    _get_local_name_from_concept_id,
    XbrlNoteTableParseError,
    _find_presentation_link,
    _find_table_locator_labels,
    _build_child_map,
    _build_locator_map,
    XLINK_NS,
    LINK_NS,
    _parse_order,
    

)
from dart.xbrl_file_service import (
    download_xbrl_archive,
)
from zipfile import ZipFile, BadZipFile
from io import BytesIO
from xml.etree import ElementTree
from collections import defaultdict
TAX_NOTE_CONSOLIDATED_ROLE_URI = (
    "http://dart.fss.or.kr/role/ifrs/"
    "ias_12_role-D835110"
)

MAJOR_TAX_COMPONENTS_TABLE = (
    "MajorComponentsOfTaxExpenseIncomeTable"
)

def get_presentation_concept_type(
    local_name: str,
) -> str:
    if local_name.endswith("Table"):
        return "TABLE"

    if local_name.endswith("Axis"):
        return "AXIS"

    if local_name.endswith("Domain"):
        return "DOMAIN"

    if local_name.endswith("Member"):
        return "MEMBER"

    if local_name.endswith("LineItems"):
        return "LINE_ITEMS"

    if local_name.endswith("Abstract"):
        return "ABSTRACT"

    if local_name.endswith("Explanatory"):
        return "EXPLANATORY"

    if local_name.endswith("TextBlock"):
        return "TEXT_BLOCK"

    return "FACT"


def inspect_table_children(
    content: bytes,
    role_uri: str,
    table_local_name: str,
) -> None:
    try:
        with ZipFile(BytesIO(content)) as archive:
            presentation_file_name = (
                _get_presentation_file_name(archive)
            )

            with archive.open(
                presentation_file_name
            ) as file:
                root = ElementTree.parse(
                    file
                ).getroot()

    except BadZipFile as error:
        raise XbrlNoteTableParseError(
            "유효한 XBRL ZIP 파일이 아닙니다."
        ) from error

    presentation_link = (
        _find_presentation_link(
            root=root,
            role_uri=role_uri,
        )
    )

    locator_map = _build_locator_map(
        presentation_link
    )
    child_map = _build_child_map(
        presentation_link
    )

    table_labels = (
        _find_table_locator_labels(
            locator_map=locator_map,
            table_local_name=(
                table_local_name
            ),
        )
    )

    for table_label in table_labels:
        print()
        print(f"Table locator: {table_label}")
        print("-" * 100)

        children = child_map.get(
            table_label,
            [],
        )

        print(f"직접 자식 수: {len(children)}")

        for order, child_label in children:
            child = locator_map.get(
                child_label
            )

            print(
                f"order={order} / "
                f"locator={child_label} / "
                f"concept={child}"
            )


def build_parent_map(
    presentation_link: ElementTree.Element,
) -> dict[str, list[tuple[float, str]]]:
    """
    자식 locator를 기준으로 부모 locator를 조회할 수 있는
    사전을 만든다.
    """
    from_attribute = f"{{{XLINK_NS}}}from"
    to_attribute = f"{{{XLINK_NS}}}to"

    parent_map: dict[
        str,
        list[tuple[float, str]],
    ] = defaultdict(list)

    for arc in presentation_link.findall(
        f"{{{LINK_NS}}}presentationArc"
    ):
        parent_label = arc.get(
            from_attribute,
            "",
        )
        child_label = arc.get(
            to_attribute,
            "",
        )

        if not parent_label or not child_label:
            continue

        order = _parse_order(
            arc.get("order")
        )

        parent_map[child_label].append(
            (order, parent_label)
        )

    return dict(parent_map)

def inspect_table_parent_and_siblings(
    content: bytes,
    role_uri: str,
    table_local_name: str,
) -> None:
    with ZipFile(BytesIO(content)) as archive:
        presentation_file_name = (
            _get_presentation_file_name(
                archive
            )
        )

        with archive.open(
            presentation_file_name
        ) as file:
            root = ElementTree.parse(
                file
            ).getroot()

    presentation_link = (
        _find_presentation_link(
            root=root,
            role_uri=role_uri,
        )
    )

    locator_map = _build_locator_map(
        presentation_link
    )
    child_map = _build_child_map(
        presentation_link
    )
    parent_map = build_parent_map(
        presentation_link
    )

    table_labels = (
        _find_table_locator_labels(
            locator_map=locator_map,
            table_local_name=(
                table_local_name
            ),
        )
    )
    print("[법인세비용 구성표]")
    print("-" * 100)

    for table_label in table_labels:
        print()
        print(
            f"[주석 테이블 구조]"
        )
        print("-" * 100)

        table = locator_map[table_label]

        print(
            f"- [TABLE] "
            f"{table['local_name']}"
        )

        parents = parent_map.get(
            table_label,
            [],
        )

        for _, parent_label in parents:
            siblings = child_map.get(
                parent_label,
                [],
            )

            for order, sibling_label in siblings:
                sibling = locator_map.get(
                    sibling_label
                )

                if sibling is None:
                    continue

                local_name = sibling[
                    "local_name"
                ]

                if sibling_label == table_label:
                    continue

                if local_name.endswith(
                    "LineItems"
                ):
                    print(
                        f"- [LINE_ITEMS] "
                        f"{local_name}"
                    )

                    for (
                        child_order,
                        child_label,
                    ) in child_map.get(
                        sibling_label,
                        [],
                    ):
                        child = locator_map.get(
                            child_label
                        )

                        if child is None:
                            continue

                        print(
                            f"    - [FACT] "
                            f"{child['local_name']}"
                        )

    for table_label in table_labels:
        print()
        print(
            f"Table: "
            f"{locator_map[table_label]}"
        )
        print("-" * 100)

        parents = parent_map.get(
            table_label,
            [],
        )

        for _, parent_label in parents:
            parent = locator_map.get(
                parent_label
            )

            print(
                f"부모: {parent}"
            )

            print("형제 목록:")

            for order, sibling_label in (
                child_map.get(
                    parent_label,
                    [],
                )
            ):
                sibling = locator_map.get(
                    sibling_label
                )

                print(
                    f"- order={order} / "
                    f"{sibling}"
                )


def main() -> None:
    content = download_xbrl_archive(
        rcept_no="20260310002820",
        reprt_code="11011",
    )

    concepts = parse_note_table_line_items(
        content=content,
        role_uri=(
            TAX_NOTE_CONSOLIDATED_ROLE_URI
        ),
        table_local_name=(
            MAJOR_TAX_COMPONENTS_TABLE
        ),
    )

    print("[법인세비용 구성표]")
    print("-" * 100)

    for concept in concepts:
        indent = "    " * concept.depth

        print(
            f"{indent}"
            f"- {concept.local_name}"
        )


if __name__ == "__main__":
    main()