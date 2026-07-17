#보조 기능 제공
from wcwidth import wcswidth
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
    if value is None:
        return "-"

    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)
