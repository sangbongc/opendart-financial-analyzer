from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from analysis.income_tax_note_service import (
    IncomeTaxNoteAnalysisError,
    _get_fact_decimal_value,
    get_major_components_of_tax_expense,
)


def _make_concept(
    concept_id: str = "tax_CurrentTaxExpenseIncome",
    local_name: str = "CurrentTaxExpenseIncome",
    depth: int = 0,
    has_children: bool = False,
) -> SimpleNamespace:
    """
    서비스 테스트에 사용할 presentation concept 대역을 생성한다.
    """
    return SimpleNamespace(
        concept_id=concept_id,
        local_name=local_name,
        depth=depth,
        has_children=has_children,
    )


def _make_fact(
    value: str | None = "9311684000000",
    is_nil: bool = False,
    unit_ref: str | None = "KRW",
    decimals: str | None = "-3",
    context_ref: str | None = "Context_2025_CFS",
) -> SimpleNamespace:
    """
    서비스 테스트에 사용할 XBRL Fact 대역을 생성한다.
    """
    return SimpleNamespace(
        value=value,
        is_nil=is_nil,
        unit_ref=unit_ref,
        decimals=decimals,
        context_ref=context_ref,
    )


def _make_note_item(
    concept_id: str = "tax_CurrentTaxExpenseIncome",
    local_name: str = "CurrentTaxExpenseIncome",
    depth: int = 0,
    has_children: bool = False,
    facts: list[object] | None = None,
) -> SimpleNamespace:
    """
    parse_note_table_items()가 반환하는 NoteTableItem 대역을 생성한다.
    """
    if facts is None:
        facts = []

    return SimpleNamespace(
        concept=_make_concept(
            concept_id=concept_id,
            local_name=local_name,
            depth=depth,
            has_children=has_children,
        ),
        facts=facts,
    )

@patch(
    "analysis.income_tax_note_service.parse_xbrl_label_map"
)
@patch(
    "analysis.income_tax_note_service.select_note_fact"
)
@patch(
    "analysis.income_tax_note_service.parse_note_table_items"
)
def test_get_major_components_calls_parser(
    mock_parse_note_table_items,
    mock_select_note_fact,
    mock_parse_xbrl_label_map,
) -> None:
    """
    법인세 주석 서비스가 범용 XBRL 파서를
    올바른 인수로 호출하는지 검증한다.
    """
    item = _make_note_item()
    selected_fact = _make_fact()
    mock_parse_xbrl_label_map.return_value = {
        "tax_CurrentTaxExpenseIncome": (
            "당기법인세비용(수익)"
        ),
    }
    mock_parse_note_table_items.return_value = [
        item
    ]
    mock_select_note_fact.return_value = (
        selected_fact
    )

    results = get_major_components_of_tax_expense(
        content=b"sample-xbrl-content",
        bsns_year="2025",
        fs_div="CFS",
    )

    mock_parse_note_table_items.assert_called_once()

    call_arguments = (
        mock_parse_note_table_items.call_args.kwargs
    )

    assert (
        call_arguments["content"]
        == b"sample-xbrl-content"
    )
    assert (
        call_arguments["table_local_name"]
        == "MajorComponentsOfTaxExpenseIncomeTable"
    )

    assert len(results) == 1


@patch(
    "analysis.income_tax_note_service.parse_xbrl_label_map"
)
@patch(
    "analysis.income_tax_note_service.select_note_fact"
)
@patch(
    "analysis.income_tax_note_service.parse_note_table_items"
)
def test_select_note_fact_is_called_for_each_item(
    mock_parse_note_table_items,
    mock_select_note_fact,
    mock_parse_xbrl_label_map,
) -> None:
    """
    각 presentation 항목마다 조건에 맞는 Fact를
    한 번씩 선택하는지 검증한다.
    """
    items = [
        _make_note_item(
            concept_id="tax_CurrentTax",
            local_name="CurrentTaxExpenseIncome",
        ),
        _make_note_item(
            concept_id="tax_DeferredTax",
            local_name="DeferredTaxExpenseIncome",
        ),
        _make_note_item(
            concept_id="tax_TotalTax",
            local_name=(
                "IncomeTaxExpenseContinuingOperations"
            ),
        ),
    ]

    mock_parse_note_table_items.return_value = (
        items
    )
    mock_select_note_fact.side_effect = [
        _make_fact(
            value="9311684000000"
        ),
        _make_fact(
            value="-5037018000000"
        ),
        _make_fact(
            value="4274666000000"
        ),
    ]

    results = get_major_components_of_tax_expense(
        content=b"sample-xbrl-content",
        bsns_year="2025",
        fs_div="CFS",
    )

    assert mock_select_note_fact.call_count == 3
    assert len(results) == 3

    for call in mock_select_note_fact.call_args_list:
        assert (
            call.kwargs["bsns_year"]
            == "2025"
        )
        assert call.kwargs["fs_div"] == "CFS"


@patch(
    "analysis.income_tax_note_service.parse_xbrl_label_map"
)
@patch(
    "analysis.income_tax_note_service.select_note_fact"
)
@patch(
    "analysis.income_tax_note_service.parse_note_table_items"
)
def test_fact_value_is_converted_to_decimal(
    mock_parse_note_table_items,
    mock_select_note_fact,
    mock_parse_xbrl_label_map,
) -> None:
    """
    선택된 Fact의 문자열 값이 Decimal로
    변환되는지 검증한다.
    """
    item = _make_note_item()

    mock_parse_note_table_items.return_value = [
        item
    ]
    mock_select_note_fact.return_value = (
        _make_fact(
            value="9,311,684,000,000"
        )
    )

    results = get_major_components_of_tax_expense(
        content=b"sample-xbrl-content",
        bsns_year="2025",
        fs_div="CFS",
    )

    assert results[0].value == Decimal(
        "9311684000000"
    )
    assert isinstance(
        results[0].value,
        Decimal,
    )


@patch(
    "analysis.income_tax_note_service.parse_xbrl_label_map"
)
@patch(
    "analysis.income_tax_note_service.select_note_fact"
)
@patch(
    "analysis.income_tax_note_service.parse_note_table_items"
)
def test_nil_fact_is_converted_to_none(
    mock_parse_note_table_items,
    mock_select_note_fact,
    mock_parse_xbrl_label_map,
) -> None:
    """
    nil Fact가 숫자로 변환되지 않고 None으로
    반환되는지 검증한다.
    """
    item = _make_note_item()

    mock_parse_note_table_items.return_value = [
        item
    ]
    mock_select_note_fact.return_value = (
        _make_fact(
            value=None,
            is_nil=True,
        )
    )

    results = get_major_components_of_tax_expense(
        content=b"sample-xbrl-content",
        bsns_year="2025",
        fs_div="CFS",
    )

    assert results[0].value is None


@patch(
    "analysis.income_tax_note_service.parse_xbrl_label_map"
)
@patch(
    "analysis.income_tax_note_service.select_note_fact"
)
@patch(
    "analysis.income_tax_note_service.parse_note_table_items"
)
def test_missing_fact_is_converted_to_none(
    mock_parse_note_table_items,
    mock_select_note_fact,
    mock_parse_xbrl_label_map,
) -> None:
    """
    조건에 맞는 Fact가 없을 때 항목은 유지하고
    값 관련 필드는 None으로 반환하는지 검증한다.
    """
    item = _make_note_item(
        concept_id="tax_NoFact",
        local_name="TaxItemWithoutFact",
    )

    mock_parse_note_table_items.return_value = [
        item
    ]
    mock_select_note_fact.return_value = None

    results = get_major_components_of_tax_expense(
        content=b"sample-xbrl-content",
        bsns_year="2025",
        fs_div="CFS",
    )

    assert len(results) == 1
    assert results[0].local_name == (
        "TaxItemWithoutFact"
    )
    assert results[0].value is None
    assert results[0].unit_ref is None
    assert results[0].decimals is None
    assert results[0].context_ref is None


@patch(
    "analysis.income_tax_note_service.parse_xbrl_label_map"
)
@patch(
    "analysis.income_tax_note_service.select_note_fact"
)
@patch(
    "analysis.income_tax_note_service.parse_note_table_items"
)
def test_presentation_structure_is_preserved(
    mock_parse_note_table_items,
    mock_select_note_fact,
    mock_parse_xbrl_label_map,
) -> None:
    """
    presentation에서 복원한 계층 정보가
    서비스 결과에도 유지되는지 검증한다.
    """
    parent_item = _make_note_item(
        concept_id="tax_CurrentTaxTotal",
        local_name=(
            "CurrentTaxExpenseIncomeAndAdjustments"
            "ForCurrentTaxOfPriorPeriods"
        ),
        depth=0,
        has_children=True,
    )

    child_item = _make_note_item(
        concept_id="tax_CurrentTax",
        local_name="CurrentTaxExpenseIncome",
        depth=1,
        has_children=False,
    )

    mock_parse_note_table_items.return_value = [
        parent_item,
        child_item,
    ]
    mock_select_note_fact.side_effect = [
        _make_fact(
            value="9311684000000"
        ),
        _make_fact(
            value="8951271000000"
        ),
    ]

    results = get_major_components_of_tax_expense(
        content=b"sample-xbrl-content",
        bsns_year="2025",
        fs_div="CFS",
    )

    assert results[0].depth == 0
    assert results[0].has_children is True

    assert results[1].depth == 1
    assert results[1].has_children is False


@patch(
    "analysis.income_tax_note_service.parse_note_table_items"
)
def test_parser_error_is_wrapped(
    mock_parse_note_table_items,
) -> None:
    """
    범용 파서에서 발생한 예외가 서비스 전용 예외로
    변환되는지 검증한다.
    """
    mock_parse_note_table_items.side_effect = (
        RuntimeError("parser failed")
    )

    with pytest.raises(
        IncomeTaxNoteAnalysisError
    ) as error_info:
        get_major_components_of_tax_expense(
            content=b"sample-xbrl-content",
            bsns_year="2025",
            fs_div="CFS",
        )

    assert (
        "법인세비용 구성표를 파싱하지 못했습니다"
        in str(error_info.value)
    )
    assert isinstance(
        error_info.value.__cause__,
        RuntimeError,
    )


@pytest.mark.parametrize(
    ("content", "bsns_year", "fs_div"),
    [
        (
            b"",
            "2025",
            "CFS",
        ),
        (
            b"sample-xbrl-content",
            "25",
            "CFS",
        ),
        (
            b"sample-xbrl-content",
            "20A5",
            "CFS",
        ),
        (
            b"sample-xbrl-content",
            "2025",
            "INVALID",
        ),
    ],
)
def test_invalid_inputs_raise_value_error(
    content: bytes,
    bsns_year: str,
    fs_div: str,
) -> None:
    """
    비어 있는 파일, 잘못된 사업연도 및
    재무제표 구분값을 거부하는지 검증한다.
    """
    with pytest.raises(ValueError):
        get_major_components_of_tax_expense(
            content=content,
            bsns_year=bsns_year,
            fs_div=fs_div,
        )


def test_invalid_fact_value_raises_analysis_error() -> None:
    """
    숫자로 변환할 수 없는 Fact 값에 대해
    서비스 전용 예외가 발생하는지 검증한다.
    """
    fact = _make_fact(
        value="not-a-number"
    )

    with pytest.raises(
        IncomeTaxNoteAnalysisError
    ) as error_info:
        _get_fact_decimal_value(fact)

    assert (
        "Fact 값을 숫자로 변환하지 못했습니다"
        in str(error_info.value)
    )

