from io import BytesIO
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree

from xbrl.exceptions import (
    XbrlNoteTableParseError,
)
from xbrl.xbrl_models import(
    NoteTableItem,
    XbrlFact,
)
from xbrl.presentation_parser import (
    parse_note_table_line_items,
)
from xbrl.xbrl_instance_parser import (
    get_instance_file_name,
    build_context_map,
    extract_facts_by_local_names,
)



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
                get_instance_file_name(
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

    context_map = build_context_map(
        instance_root
    )

    facts_by_local_name = (
        extract_facts_by_local_names(
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

