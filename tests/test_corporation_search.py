from unittest.mock import Mock, patch

import pytest

from dart.corporation_service import find_corporations


@patch(
    "dart.corporation_service.fetch_corporation_by_stock_code"
)
def test_find_corporations_by_stock_code(
    mock_fetch_by_stock_code: Mock,
) -> None:
    mock_fetch_by_stock_code.return_value = {
        "corp_code": "00126380",
        "corp_name": "삼성전자(주)",
        "stock_code": "005930",
        "is_active": 1,
    }

    result = find_corporations("005930")

    mock_fetch_by_stock_code.assert_called_once_with(
        stock_code="005930",
        active_only=True,
    )

    assert len(result) == 1
    assert result[0]["corp_name"] == "삼성전자(주)"


@patch(
    "dart.corporation_service.fetch_corporation_by_corp_code"
)
def test_find_corporations_by_corp_code(
    mock_fetch_by_corp_code: Mock,
) -> None:
    mock_fetch_by_corp_code.return_value = {
        "corp_code": "00126380",
        "corp_name": "삼성전자(주)",
        "stock_code": "005930",
        "is_active": 1,
    }

    result = find_corporations("00126380")

    mock_fetch_by_corp_code.assert_called_once_with(
        corp_code="00126380",
    )

    assert len(result) == 1
    assert result[0]["corp_code"] == "00126380"


@patch(
    "dart.corporation_service.search_corporations_by_name"
)
def test_find_corporations_by_name(
    mock_search_by_name: Mock,
) -> None:
    mock_search_by_name.return_value = [
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자(주)",
            "stock_code": "005930",
            "is_active": 1,
        },
        {
            "corp_code": "00164742",
            "corp_name": "삼성물산(주)",
            "stock_code": "028260",
            "is_active": 1,
        },
    ]

    result = find_corporations(
        " 삼성 ",
        limit=10,
    )

    mock_search_by_name.assert_called_once_with(
        keyword="삼성",
        active_only=True,
        limit=10,
    )

    assert len(result) == 2


@patch(
    "dart.corporation_service.fetch_corporation_by_stock_code"
)
def test_find_corporations_returns_empty_list_when_not_found(
    mock_fetch_by_stock_code: Mock,
) -> None:
    mock_fetch_by_stock_code.return_value = None

    result = find_corporations("999999")

    assert result == []


@patch(
    "dart.corporation_service.fetch_corporation_by_corp_code"
)
def test_inactive_corporation_is_excluded(
    mock_fetch_by_corp_code: Mock,
) -> None:
    mock_fetch_by_corp_code.return_value = {
        "corp_code": "00126380",
        "corp_name": "삼성전자(주)",
        "stock_code": "005930",
        "is_active": 0,
    }

    result = find_corporations(
        "00126380",
        active_only=True,
    )

    assert result == []


def test_find_corporations_raises_error_for_empty_query() -> None:
    with pytest.raises(
        ValueError,
        match="기업 검색어는 비어 있을 수 없습니다",
    ):
        find_corporations("   ")