from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree


LINK_NS = "http://www.xbrl.org/2003/linkbase"
XLINK_NS = "http://www.w3.org/1999/xlink"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XSI_NS = (
    "http://www.w3.org/2001/"
    "XMLSchema-instance"
)
XBRLI_NS = "http://www.xbrl.org/2003/instance"

XBRLDI_NS = (
    "http://xbrl.org/2006/xbrldi"
)

class XbrlNoteTableParseError(Exception):
    """
    XBRL 주석 테이블 구조를 파싱하지 못했을 때 발생한다.
    """


@dataclass(frozen=True)
class XbrlFact:
    """
    XBRL 인스턴스에서 추출한 하나의 Fact를 나타낸다.
    """

    concept_id: str
    local_name: str
    namespace_uri: str

    value: str | None

    context_ref: str
    context: XbrlContext | None

    unit_ref: str | None
    decimals: str | None

    is_nil: bool


@dataclass(frozen=True)
class NoteTableItem:
    """
    주석 표의 표시 구조와 실제 Fact 목록을 함께 보관한다.
    """

    concept: PresentationConcept
    facts: tuple[XbrlFact, ...]


@dataclass(frozen=True)
class PresentationConcept:
    concept_id: str
    local_name: str
    locator_label: str
    href: str
    parent_concept_id: str | None
    depth: int
    order: float
    has_children: bool

@dataclass(frozen=True)
class XbrlLabel:
    concept_id: str
    text: str
    language: str | None
    role: str | None


@dataclass(frozen=True)
class XbrlDimensionMember:
    """
    XBRL context에 포함된 하나의 차원과 Member를 나타낸다.
    """

    dimension: str
    member: str

    @property
    def dimension_local_name(self) -> str:
        return _get_qname_local_name(
            self.dimension
        )

    @property
    def member_local_name(self) -> str:
        return _get_qname_local_name(
            self.member
        )


@dataclass(frozen=True)
class XbrlContext:
    """
    XBRL Fact가 어떤 기간과 차원에 해당하는지 나타낸다.
    """

    context_id: str
    entity_identifier: str | None

    start_date: str | None
    end_date: str | None
    instant_date: str | None

    dimensions: tuple[
        XbrlDimensionMember,
        ...,
    ]

    @property
    def member_local_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            dimension.member_local_name
            for dimension in self.dimensions
        )

    def has_member(
        self,
        member_local_name: str,
    ) -> bool:
        return member_local_name in (
            self.member_local_names
        )

    @property
    def is_duration(self) -> bool:
        return (
            self.start_date is not None
            and self.end_date is not None
        )

    @property
    def is_instant(self) -> bool:
        return self.instant_date is not None
    

@dataclass(frozen=True)
class NoteTableValue:
    concept_id: str
    local_name: str
    label: str | None

    depth: int
    has_children: bool

    value: int | None
    unit_ref: str | None

    bsns_year: str
    fs_div: str


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
        has_children=bool(
            child_map.get(locator_label)
        ),
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


def _get_instance_file_name(
    archive: ZipFile,
) -> str:
    """
    XBRL ZIP 안에서 실제 Fact가 저장된
    인스턴스 파일을 찾는다.
    """
    candidates = [
        name
        for name in archive.namelist()
        if name.lower().endswith(".xbrl")
    ]

    if not candidates:
        raise XbrlNoteTableParseError(
            "XBRL 인스턴스 파일을 찾지 못했습니다."
        )

    return candidates[0]


def _split_xml_tag(
    tag: str,
) -> tuple[str, str]:
    """
    ElementTree의 Clark notation 태그를
    namespace URI와 local name으로 분리한다.

    예:
    {namespace}CurrentTaxExpenseIncome

    반환:
    (
        "namespace",
        "CurrentTaxExpenseIncome",
    )
    """
    if tag.startswith("{") and "}" in tag:
        namespace_uri, local_name = (
            tag[1:].split("}", 1)
        )

        return namespace_uri, local_name

    return "", tag


def _is_nil_element(
    element: ElementTree.Element,
) -> bool:
    """
    XBRL Fact가 xsi:nil=true인지 확인한다.
    """
    nil_value = element.get(
        f"{{{XSI_NS}}}nil",
        "",
    )

    return nil_value.lower() in {
        "true",
        "1",
    }


def _extract_facts_by_local_names(
    instance_root: ElementTree.Element,
    concepts: list[PresentationConcept],
    context_map: dict[str, XbrlContext],
) -> dict[str, list[XbrlFact]]:
    """
    presentation concept와 일치하는 Fact를 추출하고,
    각 Fact의 contextRef를 실제 XbrlContext와 연결한다.
    """
    concept_id_by_local_name = {
        concept.local_name: concept.concept_id
        for concept in concepts
    }

    target_local_names = set(
        concept_id_by_local_name
    )

    facts_by_local_name: dict[
        str,
        list[XbrlFact],
    ] = defaultdict(list)

    for element in instance_root.iter():
        namespace_uri, local_name = (
            _split_xml_tag(element.tag)
        )

        if local_name not in target_local_names:
            continue

        context_ref = element.get(
            "contextRef",
            "",
        )

        if not context_ref:
            continue

        is_nil = _is_nil_element(
            element
        )

        value = None

        if not is_nil and element.text:
            value = element.text.strip()

        fact = XbrlFact(
            concept_id=(
                concept_id_by_local_name[
                    local_name
                ]
            ),
            local_name=local_name,
            namespace_uri=namespace_uri,
            value=value,
            context_ref=context_ref,
            context=context_map.get(
                context_ref
            ),
            unit_ref=element.get(
                "unitRef"
            ),
            decimals=element.get(
                "decimals"
            ),
            is_nil=is_nil,
        )

        facts_by_local_name[
            local_name
        ].append(fact)

    return dict(facts_by_local_name)


def _get_qname_local_name(
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


def parse_note_table_items(
    content: bytes,
    role_uri: str,
    table_local_name: str,
) -> list[NoteTableItem]:
    """
    특정 주석 Table의 presentation 구조를 찾고,
    각 concept에 해당하는 XBRL Fact를 연결한다.

    현재 단계에서는 context를 필터링하지 않고
    일치하는 모든 Fact를 반환한다.
    """
    concepts = parse_note_table_line_items(
        content=content,
        role_uri=role_uri,
        table_local_name=table_local_name,
    )

    try:
        with ZipFile(
            BytesIO(content)
        ) as archive:
            instance_file_name = (
                _get_instance_file_name(
                    archive
                )
            )

            with archive.open(
                instance_file_name
            ) as file:
                instance_root = (
                    ElementTree.parse(file)
                    .getroot()
                )

    except BadZipFile as error:
        raise XbrlNoteTableParseError(
            "유효한 XBRL ZIP 파일이 아닙니다."
        ) from error

    except ElementTree.ParseError as error:
        raise XbrlNoteTableParseError(
            "XBRL 인스턴스 XML을 "
            "파싱하지 못했습니다."
        ) from error

    context_map = _build_context_map(
        instance_root
    )

    facts_by_local_name = (
        _extract_facts_by_local_names(
            instance_root=instance_root,
            concepts=concepts,
            context_map=context_map,
        )
    )

    result: list[NoteTableItem] = []

    for concept in concepts:
        facts = facts_by_local_name.get(
            concept.local_name,
            [],
        )

        result.append(
            NoteTableItem(
                concept=concept,
                facts=tuple(facts),
            )
        )

    return result


def _parse_xbrl_context(
    context_element: ElementTree.Element,
) -> XbrlContext:
    """
    하나의 xbrli:context 요소를 구조화한다.
    """
    context_id = context_element.get(
        "id",
        "",
    )

    identifier_element = (
        context_element.find(
            f".//{{{XBRLI_NS}}}identifier"
        )
    )

    entity_identifier = None

    if identifier_element is not None:
        if identifier_element.text:
            entity_identifier = (
                identifier_element.text.strip()
            )

    start_date_element = (
        context_element.find(
            f".//{{{XBRLI_NS}}}startDate"
        )
    )

    end_date_element = (
        context_element.find(
            f".//{{{XBRLI_NS}}}endDate"
        )
    )

    instant_element = (
        context_element.find(
            f".//{{{XBRLI_NS}}}instant"
        )
    )

    start_date = _get_element_text(
        start_date_element
    )
    end_date = _get_element_text(
        end_date_element
    )
    instant_date = _get_element_text(
        instant_element
    )

    dimensions: list[
        XbrlDimensionMember
    ] = []

    for member_element in (
        context_element.findall(
            f".//{{{XBRLDI_NS}}}explicitMember"
        )
    ):
        dimension = member_element.get(
            "dimension",
            "",
        )

        member = (
            member_element.text.strip()
            if member_element.text
            else ""
        )

        if not dimension or not member:
            continue

        dimensions.append(
            XbrlDimensionMember(
                dimension=dimension,
                member=member,
            )
        )

    return XbrlContext(
        context_id=context_id,
        entity_identifier=entity_identifier,
        start_date=start_date,
        end_date=end_date,
        instant_date=instant_date,
        dimensions=tuple(dimensions),
    )


def _get_element_text(
    element: ElementTree.Element | None,
) -> str | None:
    if element is None:
        return None

    if element.text is None:
        return None

    value = element.text.strip()

    return value or None


def _build_context_map(
    instance_root: ElementTree.Element,
) -> dict[str, XbrlContext]:
    """
    XBRL 인스턴스의 모든 context를 ID 기준으로 정리한다.
    """
    context_map: dict[
        str,
        XbrlContext,
    ] = {}

    for context_element in (
        instance_root.findall(
            f".//{{{XBRLI_NS}}}context"
        )
    ):
        context = _parse_xbrl_context(
            context_element
        )

        if not context.context_id:
            continue

        context_map[
            context.context_id
        ] = context

    return context_map


def select_note_fact(
    facts: tuple[XbrlFact, ...],
    bsns_year: str,
    fs_div: str = "CFS",
    prefer_reported_amount: bool = True,
) -> XbrlFact | None:
    """
    여러 context에 존재하는 Fact 중에서
    사업연도와 연결·별도 조건에 맞는 Fact를 선택한다.

    fs_div:
    - CFS: 연결재무제표
    - OFS: 별도재무제표
    """
    target_member = (
        "ConsolidatedMember"
        if fs_div == "CFS"
        else "SeparateMember"
    )

    candidates: list[
        tuple[int, XbrlFact]
    ] = []

    for fact in facts:
        if fact.is_nil:
            continue

        if fact.value is None:
            continue

        context = fact.context

        if context is None:
            continue

        period_end = (
            context.end_date
            or context.instant_date
        )

        if period_end is None:
            continue

        if not period_end.startswith(
            bsns_year
        ):
            continue

        if not context.has_member(
            target_member
        ):
            continue

        score = 0

        if context.is_duration:
            score += 10

        if (
            prefer_reported_amount
            and context.has_member(
                "ReportedAmountMember"
            )
        ):
            score += 20

        # 차원이 명확히 지정된 주석 표 Fact를 우선한다.
        score += len(
            context.dimensions
        )

        candidates.append(
            (score, fact)
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return candidates[0][1]


def _find_label_file_name(
    file_names: list[str],
) -> str:
    candidates = [
        file_name
        for file_name in file_names
        if (
            file_name.lower().endswith(".xml")
            and (
                "_lab" in file_name.lower()
                or "label" in file_name.lower()
            )
        )
    ]

    if not candidates:
        raise XbrlNoteTableParseError(
            "XBRL label 파일을 찾지 못했습니다."
        )

    korean_candidates = [
        file_name
        for file_name in candidates
        if (
            "_ko" in file_name.lower()
            or "-ko" in file_name.lower()
            or "kor" in file_name.lower()
        )
    ]

    if korean_candidates:
        return korean_candidates[0]

    return candidates[0]


def _build_label_locator_map(
    root: ElementTree.Element,
) -> dict[str, str]:
    locator_map: dict[str, str] = {}

    for locator in root.findall(
        f".//{{{LINK_NS}}}loc"
    ):
        locator_label = locator.get(
            f"{{{XLINK_NS}}}label"
        )
        href = locator.get(
            f"{{{XLINK_NS}}}href"
        )

        if not locator_label or not href:
            continue

        concept_id = href.rsplit("#", 1)[-1]

        locator_map[locator_label] = concept_id

    return locator_map


def _build_label_resource_map(
    root: ElementTree.Element,
) -> dict[str, XbrlLabel]:
    resource_map: dict[str, XbrlLabel] = {}

    for label_element in root.findall(
        f".//{{{LINK_NS}}}label"
    ):
        resource_label = label_element.get(
            f"{{{XLINK_NS}}}label"
        )

        if not resource_label:
            continue

        text = "".join(
            label_element.itertext()
        ).strip()

        if not text:
            continue

        resource_map[resource_label] = XbrlLabel(
            concept_id="",
            text=text,
            language=label_element.get(
                f"{{{XML_NS}}}lang"
            ),
            role=label_element.get(
                f"{{{XLINK_NS}}}role"
            ),
        )

    return resource_map


def _build_concept_label_map(
    root: ElementTree.Element,
    language: str = "ko",
) -> dict[str, str]:
    locator_map = _build_label_locator_map(
        root
    )
    resource_map = _build_label_resource_map(
        root
    )

    label_map: dict[str, str] = {}

    for arc in root.findall(
        f".//{{{LINK_NS}}}labelArc"
    ):
        from_label = arc.get(
            f"{{{XLINK_NS}}}from"
        )
        to_label = arc.get(
            f"{{{XLINK_NS}}}to"
        )

        if not from_label or not to_label:
            continue

        concept_id = locator_map.get(
            from_label
        )
        label = resource_map.get(
            to_label
        )

        if concept_id is None or label is None:
            continue

        if (
            label.language
            and not label.language.startswith(
                language
            )
        ):
            continue

        current = label_map.get(concept_id)

        if current is None:
            label_map[concept_id] = label.text

    return label_map


def parse_xbrl_label_map(
    content: bytes,
    language: str = "ko",
) -> dict[str, str]:
    """
    XBRL ZIP의 label linkbase를 읽어
    concept_id와 표시 라벨을 연결한다.
    """
    with ZipFile(BytesIO(content)) as archive:
        file_names = archive.namelist()

        label_file_name = _find_label_file_name(
            file_names
        )

        label_xml = archive.read(
            label_file_name
        )

    try:
        root = ElementTree.fromstring(
            label_xml
        )

    except ElementTree.ParseError as error:
        raise XbrlNoteTableParseError(
            "XBRL label XML을 파싱하지 못했습니다."
        ) from error

    return _build_concept_label_map(
        root=root,
        language=language,
    )