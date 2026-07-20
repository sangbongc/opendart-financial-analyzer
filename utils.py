#보조 기능 제공
from wcwidth import wcswidth
from decimal import Decimal, InvalidOperation
from datetime import datetime


REPORT_CODE_ALIASES = {
    "annual": "11011",
    "a": "11011",
    "사업보고서": "11011",

    "q1": "11013",
    "1q": "11013",
    "1분기": "11013",

    "half": "11012",
    "h": "11012",
    "반기": "11012",

    "q3": "11014",
    "3q": "11014",
    "3분기": "11014",
}

REPORT_CODE_NAMES = {
    "11011": "사업보고서",
    "11013": "1분기보고서",
    "11012": "반기보고서",
    "11014": "3분기보고서",
}

FS_DIV_ALIASES = {
    "cfs": "CFS",
    "연결": "CFS",
    "연결재무제표": "CFS",

    "ofs": "OFS",
    "별도": "OFS",
    "개별": "OFS",
    "별도재무제표": "OFS",
}
def truncate_text(
    text: str,
    width: int,
    suffix: str = "...",
) -> str:
    """
    문자열의 실제 콘솔 표시 폭이 width를 넘으면 잘라낸다.
    """
    if wcswidth(text) <= width:
        return text

    suffix_width = wcswidth(suffix)
    target_width = width - suffix_width

    result = ""
    current_width = 0

    for char in text:
        char_width = wcswidth(char)

        if char_width < 0:
            char_width = 0

        if current_width + char_width > target_width:
            break

        result += char
        current_width += char_width

    return result + suffix

def pad(text: str, width: int) -> str:
    text = truncate_text(text, width)
    """
    출력 왼쪽 정렬 기능
    """
    return text + " " * max(
        0,
        width - wcswidth(text),
    )

def pad_right(text: str, width: int) -> str:
    """
    한글 등 실제 출력 폭을 고려하여 오른쪽 정렬한다.
    """
    text = truncate_text(text, width)

    return " " * max(
        0,
        width - wcswidth(text),
    ) + text


def format_amount(value: object) -> str:
    """
    숫자 또는 Decimal 값을 천 단위 구분기호가 포함된 문자열로 변환한다.
    값이 없거나 숫자로 변환할 수 없으면 '-'를 반환한다.
    """
    if value is None:
        return "-"

    try:
        amount = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    return f"{amount:,.0f}"


def format_ratio(value: object) -> str:
    """
    증감률을 소수점 둘째 자리까지 표시한다.
    전기 금액이 0이어서 계산할 수 없는 경우 '-'를 반환한다.
    """
    if value is None:
        return "-"

    try:
        ratio = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    return f"{ratio:,.2f}%"


def get_current_time() -> str:
    """
    현재 시각을 SQLite에 저장하기 좋은 문자열로 반환한다.
    """
    return datetime.now().isoformat(
        sep=" ",
        timespec="seconds",
    )


def format_signed_amount(
    value: object,
) -> str:
    """
    증감액에 증가·감소 부호를 붙여 출력한다.
    """
    if value is None:
        return "-"

    try:
        number = int(value)
    except (TypeError, ValueError):
        return str(value)

    return f"{number:+,}"


def format_change_ratio(
    value: object,
) -> str:
    """
    증감률을 부호와 백분율 형식으로 출력한다.
    """
    if value is None:
        return "계산 불가"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    return f"{number:+.2f}%"


