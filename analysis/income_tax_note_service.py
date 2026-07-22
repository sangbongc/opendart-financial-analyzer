from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from analysis.xbrl_note_table_parser import (
    NoteTableItem,
    XbrlFact,
    parse_note_table_items,
    select_note_fact,
    parse_xbrl_label_map,
)


# 실제 프로젝트에서 사용 중인 role URI와
# Table local name으로 교체한다.
MAJOR_COMPONENTS_OF_TAX_EXPENSE_ROLE_URI = (
    "http://dart.fss.or.kr/role/ifrs/"
    "ias_12_role-D835110"
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
        items = parse_note_table_items(
            content=content,
            role_uri=(
                MAJOR_COMPONENTS_OF_TAX_EXPENSE_ROLE_URI
            ),
            table_local_name=(
                MAJOR_COMPONENTS_OF_TAX_EXPENSE_TABLE
            ),
        )
        label_map = parse_xbrl_label_map(
            content=content,
            language="ko",
        )

    except Exception as error:
        raise IncomeTaxNoteAnalysisError(
            "법인세비용 구성표를 파싱하지 못했습니다."
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