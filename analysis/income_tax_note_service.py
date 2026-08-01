from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from xbrl.xbrl_label_parser import (
    parse_xbrl_label_map,
)
from xbrl.xbrl_models import (
    NoteTableItem,
    XbrlFact,
)
from xbrl.exceptions import (
    XbrlNoteTableParseError,
)
from xbrl.presentation_parser import (
    find_presentation_table_candidates,
)
from xbrl.xbrl_note_table_parser import (
    parse_note_table_items,
    select_note_fact,
)
from dart.disclosure_service import (
    find_financial_report_rcept_no,
)
from dart.xbrl_file_service import (
    download_xbrl_archive,
)


MAJOR_COMPONENTS_OF_TAX_EXPENSE_TABLE = (
    "MajorComponentsOfTaxExpenseIncomeTable"
)


class IncomeTaxNoteAnalysisError(Exception):
    """
    법인세 주석 분석 과정에서 발생한 오류.
    """


@dataclass(frozen=True)
class IncomeTaxNoteValue:
    concept_id: str
    local_name: str
    label: str | None

    depth: int
    has_children: bool

    value: Decimal | None
    unit_ref: str | None
    decimals: str | None
    context_ref: str | None

    bsns_year: str
    fs_div: str


def get_major_components_of_tax_expense(
    content: bytes,
    bsns_year: str,
    fs_div: str = "CFS",
) -> list[IncomeTaxNoteValue]:
    """
    XBRL ZIP에서 법인세비용 주요 구성항목을 추출한다.

    처리 과정:
    1. 법인세비용 구성표의 presentation 계층을 복원한다.
    2. 각 concept에 연결된 Fact를 찾는다.
    3. 사업연도와 연결·별도 기준에 맞는 Fact를 선택한다.
    4. 분석 및 출력에 사용하기 좋은 결과형으로 변환한다.

    Args:
        content:
            OpenDART에서 내려받은 XBRL ZIP 파일의 bytes.

        bsns_year:
            조회할 사업연도. 예: "2025"

        fs_div:
            CFS는 연결재무제표,
            OFS는 별도재무제표.

    Returns:
        법인세비용 구성표의 표시 순서와 계층을 유지한 결과 목록.
    """
    _validate_inputs(
        content=content,
        bsns_year=bsns_year,
        fs_div=fs_div,
    )

    try:
        items = _find_major_components_items(
            content=content,
            bsns_year=bsns_year,
            fs_div=fs_div,
        )

        label_map = parse_xbrl_label_map(
            content=content,
            language="ko",
        )

    except IncomeTaxNoteAnalysisError:
        raise

    except Exception as error:
        raise IncomeTaxNoteAnalysisError(
            "법인세비용 구성표를 파싱하지 못했습니다: "
            f"{error}"
        ) from error

    return [
        _convert_to_income_tax_note_value(
            item=item,
            label_map=label_map,
            bsns_year=bsns_year,
            fs_div=fs_div,
        )
        for item in items
    ]


def get_income_tax_note_by_corporation(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> list[IncomeTaxNoteValue]:
    """
    기업과 사업연도를 기준으로 법인세비용 주석을 조회한다.
    """
    rcept_no = find_financial_report_rcept_no(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
    )

    if rcept_no is None:
        raise IncomeTaxNoteAnalysisError(
            "해당 사업연도의 정기보고서를 찾지 못했습니다."
        )

    content = download_xbrl_archive(
        rcept_no=rcept_no,
        reprt_code=reprt_code,
    )

    return get_major_components_of_tax_expense(
        content=content,
        bsns_year=bsns_year,
        fs_div=fs_div,
    )



def _find_major_components_items(
    content: bytes,
    bsns_year: str,
    fs_div: str,
) -> list[NoteTableItem]:
    """
    presentation 전체에서 법인세비용 구성표와 동일한
    Table concept을 찾고, 후보 role 중 요청한 사업연도와
    재무제표 구분에 맞는 Fact가 가장 많은 role을 선택한다.

    회사별 extension role을 사용하는 경우에도
    role URI를 하드코딩하지 않고 처리한다.
    """
    try:
        candidates = find_presentation_table_candidates(
            content=content,
            table_local_name=(
                MAJOR_COMPONENTS_OF_TAX_EXPENSE_TABLE
            ),
        )

    except Exception as error:
        raise IncomeTaxNoteAnalysisError(
            "법인세비용 구성표 후보를 탐색하지 못했습니다: "
            f"{error}"
        ) from error

    exact_candidates = candidates

    if not exact_candidates:
        raise IncomeTaxNoteAnalysisError(
            "법인세비용 구성표 Table concept를 "
            "찾지 못했습니다: "
            f"{MAJOR_COMPONENTS_OF_TAX_EXPENSE_TABLE}"
        )

    best_items: list[NoteTableItem] | None = None
    best_score = -1
    candidate_errors: list[str] = []

    for candidate in exact_candidates:
        try:
            items = parse_note_table_items(
                content=content,
                role_uri=candidate.role_uri,
                table_local_name=candidate.local_name,
            )

        except XbrlNoteTableParseError as error:
            candidate_errors.append(
                f"{candidate.role_uri}: {error}"
            )
            continue

        score = _count_matching_facts(
            items=items,
            bsns_year=bsns_year,
            fs_div=fs_div,
        )

        if score > best_score:
            best_items = items
            best_score = score

    if best_items is None:
        details = " / ".join(candidate_errors)

        message = (
            "발견된 법인세비용 구성표 후보를 "
            "모두 파싱하지 못했습니다."
        )

        if details:
            message += f" 원인: {details}"

        raise IncomeTaxNoteAnalysisError(
            message
        )

    if best_score <= 0:
        roles = ", ".join(
            candidate.role_uri
            for candidate in exact_candidates
        )

        raise IncomeTaxNoteAnalysisError(
            "법인세비용 구성표는 찾았지만 "
            f"{bsns_year}년 {fs_div} 조건에 맞는 "
            "Fact를 찾지 못했습니다. "
            f"확인한 role: {roles}"
        )

    return best_items


def _count_matching_facts(
    items: list[NoteTableItem],
    bsns_year: str,
    fs_div: str,
) -> int:
    """
    주석 표 항목 중 요청한 사업연도와 재무제표 구분에
    맞는 Fact가 선택되는 항목 수를 반환한다.
    """
    return sum(
        1
        for item in items
        if select_note_fact(
            facts=item.facts,
            bsns_year=bsns_year,
            fs_div=fs_div,
        )
        is not None
    )

def _convert_to_income_tax_note_value(
    item: NoteTableItem,
    label_map: dict[str, str],
    bsns_year: str,
    fs_div: str,
) -> IncomeTaxNoteValue:
    selected_fact = select_note_fact(
        facts=item.facts,
        bsns_year=bsns_year,
        fs_div=fs_div,
    )

    return IncomeTaxNoteValue(
        concept_id=item.concept.concept_id,
        local_name=item.concept.local_name,
        label=label_map.get(
            item.concept.concept_id
        ),
        depth=item.concept.depth,
        has_children=item.concept.has_children,
        value=_get_fact_decimal_value(
            selected_fact
        ),
        unit_ref=(
            selected_fact.unit_ref
            if selected_fact is not None
            else None
        ),
        decimals=(
            selected_fact.decimals
            if selected_fact is not None
            else None
        ),
        context_ref=(
            selected_fact.context_ref
            if selected_fact is not None
            else None
        ),
        bsns_year=bsns_year,
        fs_div=fs_div,
    )


def _get_fact_decimal_value(
    fact: XbrlFact | None,
) -> Decimal | None:
    """
    선택된 XBRL Fact의 문자열 값을 Decimal로 변환한다.
    """
    if fact is None:
        return None

    if fact.is_nil:
        return None

    if fact.value is None:
        return None

    try:
        return Decimal(
            fact.value.replace(",", "")
        )

    except InvalidOperation as error:
        raise IncomeTaxNoteAnalysisError(
            "법인세 주석 Fact 값을 숫자로 "
            f"변환하지 못했습니다: {fact.value}"
        ) from error


def _validate_inputs(
    content: bytes,
    bsns_year: str,
    fs_div: str,
) -> None:
    """
    법인세 주석 분석 입력값을 검증한다.
    """
    if not content:
        raise ValueError(
            "XBRL 파일 내용이 비어 있습니다."
        )

    if (
        len(bsns_year) != 4
        or not bsns_year.isdigit()
    ):
        raise ValueError(
            "bsns_year는 4자리 숫자 문자열이어야 합니다."
        )

    if fs_div not in {
        "CFS",
        "OFS",
    }:
        raise ValueError(
            "fs_div는 CFS 또는 OFS여야 합니다."
        )