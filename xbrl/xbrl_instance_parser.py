from xml.etree import ElementTree
from collections import defaultdict
from zipfile import ZipFile

from xbrl.exceptions import (
    XbrlNoteTableParseError,
)
from xbrl.constants import (
    XSI_NS,
    XBRLI_NS,
    XBRLDI_NS,
)
from xbrl.xbrl_models import (
    XbrlFact,
    XbrlDimensionMember,
    XbrlContext,
    PresentationConcept,
)


def get_instance_file_name(
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



def extract_facts_by_local_names(
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


def build_context_map(
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
