from io import BytesIO
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree

from xbrl.exceptions import (
    XbrlNoteTableParseError,
)
from xbrl.xbrl_models import (
    XbrlLabel,
)
from xbrl.constants import (
    LINK_NS,
    XLINK_NS,
)


XML_NS = "http://www.w3.org/XML/1998/namespace"


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
    try:
        with ZipFile(
            BytesIO(content)
        ) as archive:
            label_file_name = (
                _find_label_file_name(
                    archive.namelist()
                )
            )

            label_xml = archive.read(
                label_file_name
            )

    except BadZipFile as error:
        raise XbrlNoteTableParseError(
            "유효한 XBRL ZIP 파일이 아닙니다."
        ) from error
    
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