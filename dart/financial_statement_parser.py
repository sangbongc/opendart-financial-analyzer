from typing import Any


class FinancialStatementParseError(Exception):
    """재무제표 API 응답을 파싱할 수 없을 때 발생하는 예외입니다."""


def parse_amount(value: Any) -> int | None:
    """
    OpenDART의 금액 문자열을 정수로 변환한다.

    변환 예시
    ----------
    "1,234,567" -> 1234567
    "-1,234"    -> -1234
    ""          -> None
    None        -> None
    """
    if value is None:
        return None

    if isinstance(value, bool):
        raise FinancialStatementParseError(
            "금액에는 bool 값을 사용할 수 없습니다."
        )

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if not value.is_integer():
            raise FinancialStatementParseError(
                f"정수가 아닌 금액입니다: {value}"
            )

        return int(value)

    if not isinstance(value, str):
        raise FinancialStatementParseError(
            f"지원하지 않는 금액 타입입니다: {type(value).__name__}"
        )

    normalized = (
        value.strip()
        .replace(",", "")
        .replace(" ", "")
    )

    if normalized in {"", "-", "－"}:
        return None

    # 일부 재무 데이터에서 괄호로 음수를 표현하는 경우에 대비한다.
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"

    try:
        return int(normalized)

    except ValueError as error:
        raise FinancialStatementParseError(
            f"금액을 정수로 변환할 수 없습니다: {value!r}"
        ) from error


def parse_order(value: Any) -> int | None:
    """
    DART 계정과목 정렬순서를 정수로 변환한다.
    """
    if value is None:
        return None

    normalized = str(value).strip()

    if not normalized:
        return None

    try:
        return int(normalized)

    except ValueError as error:
        raise FinancialStatementParseError(
            f"계정과목 정렬순서를 변환할 수 없습니다: {value!r}"
        ) from error


def normalize_text(value: Any) -> str | None:
    """
    문자열의 앞뒤 공백을 제거하고 빈 문자열은 None으로 변환한다.
    """
    if value is None:
        return None

    normalized = str(value).strip()

    return normalized or None


def parse_financial_statement_row(
    row: dict[str, Any],
) -> dict[str, Any]:
    """
    OpenDART 전체 재무제표 API의 한 행을 정규화한다.
    """
    if not isinstance(row, dict):
        raise FinancialStatementParseError(
            "재무제표 행은 딕셔너리여야 합니다."
        )

    required_fields = {
        "rcept_no",
        "reprt_code",
        "bsns_year",
        "corp_code",
        "sj_div",
        "account_nm",
    }

    missing_fields = [
        field
        for field in required_fields
        if not normalize_text(row.get(field))
    ]

    if missing_fields:
        joined_fields = ", ".join(sorted(missing_fields))

        raise FinancialStatementParseError(
            f"필수 재무제표 필드가 없습니다: {joined_fields}"
        )

    return {
        "rcept_no": normalize_text(row.get("rcept_no")),
        "reprt_code": normalize_text(row.get("reprt_code")),
        "bsns_year": normalize_text(row.get("bsns_year")),
        "corp_code": normalize_text(row.get("corp_code")),
        "fs_div": normalize_text(row.get("fs_div")),
        "fs_nm": normalize_text(row.get("fs_nm")),
        "sj_div": normalize_text(row.get("sj_div")),
        "sj_nm": normalize_text(row.get("sj_nm")),
        "account_id": normalize_text(row.get("account_id")),
        "account_nm": normalize_text(row.get("account_nm")),
        "account_detail": normalize_text(
            row.get("account_detail")
        ),
        "thstrm_nm": normalize_text(row.get("thstrm_nm")),
        "thstrm_amount": parse_amount(
            row.get("thstrm_amount")
        ),
        "thstrm_add_amount": parse_amount(
            row.get("thstrm_add_amount")
        ),
        "frmtrm_nm": normalize_text(row.get("frmtrm_nm")),
        "frmtrm_amount": parse_amount(
            row.get("frmtrm_amount")
        ),
        "frmtrm_q_nm": normalize_text(
            row.get("frmtrm_q_nm")
        ),
        "frmtrm_q_amount": parse_amount(
            row.get("frmtrm_q_amount")
        ),
        "frmtrm_add_amount": parse_amount(
            row.get("frmtrm_add_amount")
        ),
        "bfefrmtrm_nm": normalize_text(
            row.get("bfefrmtrm_nm")
        ),
        "bfefrmtrm_amount": parse_amount(
            row.get("bfefrmtrm_amount")
        ),
        "ord": parse_order(row.get("ord")),
        "currency": normalize_text(row.get("currency")),
    }


def parse_financial_statement_response(
    response: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    OpenDART 전체 재무제표 API 응답을 정규화된 행 목록으로 변환한다.

    DartClient가 이미 status 검사를 수행하므로 이 함수는
    응답 구조와 각 행의 데이터 형식에 집중한다.
    """
    if not isinstance(response, dict):
        raise FinancialStatementParseError(
            "OpenDART 응답은 딕셔너리여야 합니다."
        )

    rows = response.get("list")

    if rows is None:
        raise FinancialStatementParseError(
            "OpenDART 응답에 list 필드가 없습니다."
        )

    if not isinstance(rows, list):
        raise FinancialStatementParseError(
            "OpenDART 응답의 list 필드는 리스트여야 합니다."
        )

    parsed_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        try:
            parsed_row = parse_financial_statement_row(row)

        except FinancialStatementParseError as error:
            raise FinancialStatementParseError(
                f"{index + 1}번째 재무제표 행 파싱 실패: {error}"
            ) from error

        parsed_rows.append(parsed_row)

    return parsed_rows