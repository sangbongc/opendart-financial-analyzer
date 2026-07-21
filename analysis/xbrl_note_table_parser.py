from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree


LINK_NS = "http://www.xbrl.org/2003/linkbase"
XLINK_NS = "http://www.w3.org/1999/xlink"


class XbrlNoteTableParseError(Exception):
    """
    XBRL 주석 테이블 구조를 파싱하지 못했을 때 발생한다.
    """


@dataclass(frozen=True)
class PresentationConcept:
    """
    Presentation linkbase에서 확인한 하나의 concept를 나타낸다.
    """

    concept_id: str
    local_name: str
    locator_label: str
    href: str
    parent_concept_id: str | None
    depth: int
    order: float


def _get_presentation_file_name(
    archive: ZipFile,
) -> str:
    """
    XBRL ZIP 안에서 presentation linkbase 파일을 찾는다.
    """
    file_name = next(
        (
            name
            for name in archive.namelist()
            if name.lower().endswith("_pre.xml")
        ),
        None,
    )

    if file_name is None:
        raise XbrlNoteTableParseError(
            "presentation linkbase 파일을 찾지 못했습니다."
        )

    return file_name


def _get_concept_id_from_href(
    href: str,
) -> str:
    """
    locator의 href에서 concept ID를 추출한다.

    예:
    ...xsd#ifrs-full_AccountingProfit
        -> ifrs-full_AccountingProfit
    """
    if "#" not in href:
        return ""

    return href.rsplit("#", 1)[-1]


def _get_local_name_from_concept_id(
    concept_id: str,
) -> str:
    """
    concept ID에서 namespace prefix를 제외한 이름을 반환한다.

    예:
    ifrs-full_AccountingProfit
        -> AccountingProfit

    entity00126380_CustomTaxItem
        -> CustomTaxItem
    """
    if "_" not in concept_id:
        return concept_id

    return concept_id.split("_", 1)[-1]


def _parse_order(value: str | None) -> float:
    """
    presentationArc의 order 값을 정렬 가능한 숫자로 변환한다.
    """
    if value is None:
        return 0.0

    try:
        return float(value)
    except ValueError:
        return 0.0


def _find_presentation_link(
    root: ElementTree.Element,
    role_uri: str,
) -> ElementTree.Element:
    """
    지정한 role URI에 해당하는 presentationLink를 찾는다.
    """
    role_attribute = f"{{{XLINK_NS}}}role"

    for presentation_link in root.findall(
        f".//{{{LINK_NS}}}presentationLink"
    ):
        current_role_uri = presentation_link.get(
            role_attribute,
            "",
        )

        if current_role_uri == role_uri:
            return presentation_link

    raise XbrlNoteTableParseError(
        f"presentation role을 찾지 못했습니다: "
        f"{role_uri}"
    )


def _build_locator_map(
    presentation_link: ElementTree.Element,
) -> dict[str, dict[str, str]]:
    """
    locator label을 기준으로 concept 정보를 조회할 수 있는
    사전을 만든다.

    반환 예:
    {
        "Loc_label_...": {
            "concept_id": "ifrs-full_AccountingProfit",
            "local_name": "AccountingProfit",
            "href": "...",
        }
    }
    """
    label_attribute = f"{{{XLINK_NS}}}label"
    href_attribute = f"{{{XLINK_NS}}}href"

    locator_map: dict[str, dict[str, str]] = {}

    for locator in presentation_link.findall(
        f"{{{LINK_NS}}}loc"
    ):
        locator_label = locator.get(
            label_attribute,
            "",
        )
        href = locator.get(
            href_attribute,
            "",
        )

        concept_id = _get_concept_id_from_href(
            href
        )

        if not locator_label or not concept_id:
            continue

        locator_map[locator_label] = {
            "concept_id": concept_id,
            "local_name": (
                _get_local_name_from_concept_id(
                    concept_id
                )
            ),
            "href": href,
        }

    return locator_map


def _build_child_map(
    presentation_link: ElementTree.Element,
) -> dict[str, list[tuple[float, str]]]:
    """
    presentationArc를 이용해 부모 locator와 자식 locator의
    관계를 만든다.

    반환 예:
    {
        "부모 locator label": [
            (1.0, "자식 locator label"),
            (2.0, "다른 자식 locator label"),
        ]
    }
    """
    from_attribute = f"{{{XLINK_NS}}}from"
    to_attribute = f"{{{XLINK_NS}}}to"

    child_map: dict[
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

        child_map[parent_label].append(
            (order, child_label)
        )

    for children in child_map.values():
        children.sort(
            key=lambda item: item[0]
        )

    return dict(child_map)


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


def _find_table_locator_labels(
    locator_map: dict[str, dict[str, str]],
    table_local_name: str,
) -> list[str]:
    """
    원하는 Table concept에 해당하는 locator label을 찾는다.
    """
    result: list[str] = []

    for locator_label, concept in (
        locator_map.items()
    ):
        if (
            concept["local_name"]
            == table_local_name
        ):
            result.append(locator_label)

    if not result:
        raise XbrlNoteTableParseError(
            f"주석 테이블을 찾지 못했습니다: "
            f"{table_local_name}"
        )

    return result


def _walk_presentation_tree(
    locator_label: str,
    locator_map: dict[str, dict[str, str]],
    child_map: dict[
        str,
        list[tuple[float, str]],
    ],
    parent_concept_id: str | None = None,
    depth: int = 0,
    order: float = 0.0,
    visited: set[str] | None = None,
) -> list[PresentationConcept]:
    """
    지정한 locator부터 presentation 구조를 재귀적으로 순회한다.
    """
    if visited is None:
        visited = set()

    if locator_label in visited:
        return []

    visited.add(locator_label)

    concept = locator_map.get(
        locator_label
    )

    if concept is None:
        return []

    current = PresentationConcept(
        concept_id=concept["concept_id"],
        local_name=concept["local_name"],
        locator_label=locator_label,
        href=concept["href"],
        parent_concept_id=parent_concept_id,
        depth=depth,
        order=order,
    )

    result = [current]

    for child_order, child_label in (
        child_map.get(locator_label, [])
    ):
        result.extend(
            _walk_presentation_tree(
                locator_label=child_label,
                locator_map=locator_map,
                child_map=child_map,
                parent_concept_id=(
                    current.concept_id
                ),
                depth=depth + 1,
                order=child_order,
                visited=visited,
            )
        )

    return result


def parse_note_table_line_items(
    content: bytes,
    role_uri: str,
    table_local_name: str,
) -> list[PresentationConcept]:
    """
    지정한 주석 Table에 대응하는 LineItems 아래의
    concept 구조를 반환한다.
    """
    try:
        with ZipFile(
            BytesIO(content)
        ) as archive:
            presentation_file_name = (
                _get_presentation_file_name(
                    archive
                )
            )

            with archive.open(
                presentation_file_name
            ) as file:
                root = (
                    ElementTree.parse(file)
                    .getroot()
                )

    except BadZipFile as error:
        raise XbrlNoteTableParseError(
            "유효한 XBRL ZIP 파일이 아닙니다."
        ) from error

    except ElementTree.ParseError as error:
        raise XbrlNoteTableParseError(
            "presentation linkbase XML을 "
            "파싱하지 못했습니다."
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

    parent_map = build_parent_map(
        presentation_link
    )

    table_labels = (
        _find_table_locator_labels(
            locator_map=locator_map,
            table_local_name=table_local_name,
        )
    )

    table_base_name = (
        table_local_name.removesuffix(
            "Table"
        )
    )

    expected_line_items_name = (
        table_base_name
        + "LineItems"
    )

    result: list[
        PresentationConcept
    ] = []

    for table_label in table_labels:
        parents = parent_map.get(
            table_label,
            [],
        )

        for _, parent_label in parents:
            siblings = child_map.get(
                parent_label,
                [],
            )

            for _, sibling_label in siblings:
                sibling = locator_map.get(
                    sibling_label
                )

                if sibling is None:
                    continue

                if (
                    sibling["local_name"]
                    != expected_line_items_name
                ):
                    continue

                line_item_children = (
                    child_map.get(
                        sibling_label,
                        [],
                    )
                )

                for order, child_label in (
                    line_item_children
                ):
                    child = locator_map.get(
                        child_label
                    )

                    if child is None:
                        continue

                    result.extend(
                        _walk_presentation_tree(
                            locator_label=(
                                child_label
                            ),
                            locator_map=locator_map,
                            child_map=child_map,
                            parent_concept_id=(
                                sibling["concept_id"]
                            ),
                            depth=0,
                            order=order,
                        )
                    )

    if not result:
        raise XbrlNoteTableParseError(
            "주석 테이블의 LineItems를 "
            "찾지 못했습니다: "
            f"{table_local_name}"
        )

    return result