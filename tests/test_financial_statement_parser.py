import pytest

from dart.financial_statement_parser import (
    FinancialStatementParseError,
    parse_amount,
    parse_financial_statement_response,
    parse_financial_statement_row,
)


def test_parse_amount_removes_commas() -> None:
    assert parse_amount("1,234,567") == 1234567


def test_parse_amount_supports_negative_value() -> None:
    assert parse_amount("-1,234") == -1234


def test_parse_amount_supports_parentheses_negative_value() -> None:
    assert parse_amount("(1,234)") == -1234


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
        "-",
        "－",
    ],
)
def test_parse_amount_returns_none_for_empty_value(
    value: object,
) -> None:
    assert parse_amount(value) is None


def test_parse_amount_raises_error_for_invalid_value() -> None:
    with pytest.raises(
        FinancialStatementParseError,
        match="금액을 정수로 변환할 수 없습니다",
    ):
        parse_amount("금액없음")


def test_parse_financial_statement_row() -> None:
    source_row = {
        "rcept_no": "20260311000514",
        "reprt_code": "11011",
        "bsns_year": "2025",
        "corp_code": "00126380",
        "fs_div": "CFS",
        "fs_nm": "연결재무제표",
        "sj_div": "BS",
        "sj_nm": "연결 재무상태표",
        "account_id": "ifrs-full_Assets",
        "account_nm": "자산총계",
        "account_detail": "",
        "thstrm_nm": "제57기",
        "thstrm_amount": "455,905,980,000,000",
        "thstrm_add_amount": "",
        "frmtrm_nm": "제56기말",
        "frmtrm_amount": "448,424,507,000,000",
        "frmtrm_q_nm": "",
        "frmtrm_q_amount": "",
        "frmtrm_add_amount": "",
        "bfefrmtrm_nm": "제55기말",
        "bfefrmtrm_amount": "455,105,980,000,000",
        "ord": "1",
        "currency": "KRW",
    }

    parsed = parse_financial_statement_row(source_row)

    assert parsed["corp_code"] == "00126380"
    assert parsed["fs_div"] == "CFS"
    assert parsed["sj_div"] == "BS"
    assert parsed["account_nm"] == "자산총계"
    assert parsed["account_detail"] is None
    assert parsed["thstrm_amount"] == 455905980000000
    assert parsed["frmtrm_amount"] == 448424507000000
    assert parsed["thstrm_add_amount"] is None
    assert parsed["ord"] == 1


def test_parse_financial_statement_response() -> None:
    response = {
        "status": "000",
        "message": "정상",
        "list": [
            {
                "rcept_no": "20260311000514",
                "reprt_code": "11011",
                "bsns_year": "2025",
                "corp_code": "00126380",
                "fs_div": "CFS",
                "fs_nm": "연결재무제표",
                "sj_div": "IS",
                "sj_nm": "연결 손익계산서",
                "account_id": "ifrs-full_Revenue",
                "account_nm": "매출액",
                "account_detail": "",
                "thstrm_nm": "제57기",
                "thstrm_amount": "300,000,000",
                "thstrm_add_amount": "",
                "frmtrm_nm": "제56기",
                "frmtrm_amount": "250,000,000",
                "frmtrm_q_nm": "",
                "frmtrm_q_amount": "",
                "frmtrm_add_amount": "",
                "bfefrmtrm_nm": "제55기",
                "bfefrmtrm_amount": "200,000,000",
                "ord": "10",
                "currency": "KRW",
            }
        ],
    }

    parsed_rows = parse_financial_statement_response(response)

    assert len(parsed_rows) == 1
    assert parsed_rows[0]["account_nm"] == "매출액"
    assert parsed_rows[0]["thstrm_amount"] == 300000000


def test_parse_response_raises_error_when_list_is_missing() -> None:
    response = {
        "status": "000",
        "message": "정상",
    }

    with pytest.raises(
        FinancialStatementParseError,
        match="list 필드가 없습니다",
    ):
        parse_financial_statement_response(response)


def test_parse_row_raises_error_when_required_field_is_missing() -> None:
    source_row = {
        "rcept_no": "20260311000514",
        "reprt_code": "11011",
        "bsns_year": "2025",
        "corp_code": "00126380",
        "sj_div": "BS",
    }

    with pytest.raises(
        FinancialStatementParseError,
        match="account_nm",
    ):
        parse_financial_statement_row(source_row)