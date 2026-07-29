import re
from collections.abc import Sequence

from bs4 import BeautifulSoup, Tag


_NUMBER_PREFIX_PATTERN = re.compile(
    r"^\s*(?:\d+[.)]|[가-힣][.)]|\([0-9가-힣]+\))\s*"
)

DOCUMENT_BLOCK_TAGS = {
    # 일반 HTML
    "p",
    "div",
    "td",
    "th",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",

    # DART XML
    "title",
    "tu",
    "te",
}

_SENTENCE_ENDINGS = (
    ".",
    "!",
    "?",
    ":",
    "：",
)


def strip_number_prefix(text: str) -> str:
    return _NUMBER_PREFIX_PATTERN.sub("", text).strip()


def normalize_heading(text: str) -> str:
    return "".join(text.split()).strip()


def normalize_block_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def join_text_blocks(
    blocks: list[str],
) -> str:
    cleaned: list[str] = []

    for block in blocks:
        normalized = normalize_block_text(
            block
        )

        if normalized:
            cleaned.append(normalized)

    return "\n\n".join(cleaned)


def _create_soup(
    document: str,
) -> BeautifulSoup:
    stripped = document.lstrip()

    if stripped.startswith(
        "<?xml"
    ):
        return BeautifulSoup(
            document,
            "xml",
        )

    return BeautifulSoup(
        document,
        "html.parser",
    )


def extract_document_blocks(
    soup: BeautifulSoup,
) -> list[Tag]:
    candidates = soup.find_all(
        lambda tag: (
            isinstance(tag, Tag)
            and tag.name
            and tag.name.lower()
            in DOCUMENT_BLOCK_TAGS
        )
    )

    blocks: list[Tag] = []

    for tag in candidates:
        text = tag.get_text(
            " ",
            strip=True,
        )

        if not text:
            continue

        parent = tag.find_parent(
            lambda parent: (
                isinstance(parent, Tag)
                and parent.name
                and parent.name.lower()
                in DOCUMENT_BLOCK_TAGS
            )
        )

        if (
            parent is not None
            and parent.get_text(
                " ",
                strip=True,
            ) == text
        ):
            continue

        blocks.append(tag)

    return blocks


def is_bold_element(
    element: Tag,
) -> bool:
    if element.name in {
        "b",
        "strong",
    }:
        return True

    if element.find(
        ["b", "strong"]
    ) is not None:
        return True

    for tag in element.find_all(True):
        usermark = str(
            tag.attrs.get(
                "USERMARK",
                tag.attrs.get(
                    "usermark",
                    "",
                ),
            )
        ).upper()

        if usermark == "B":
            return True

        style = str(
            tag.attrs.get(
                "style",
                "",
            )
        ).lower()

        compact_style = style.replace(
            " ",
            ""
        )

        if (
            "font-weight:bold"
            in compact_style
            or "font-weight:700"
            in compact_style
        ):
            return True

    return False


def is_standalone_heading(
    text: str,
    headings: set[str],
) -> bool:
    """
    텍스트 블록 전체가 지정된 섹션 제목인지 확인한다.

    '기타사항(전기감사인 관련)'처럼 제목 뒤에
    괄호 설명이 붙은 경우도 제목으로 인정한다.
    """
    normalized = normalize_heading(
        strip_number_prefix(text)
    )

    normalized_headings = {
        normalize_heading(heading)
        for heading in headings
    }

    if normalized in normalized_headings:
        return True

    return any(
        normalized.startswith(
            f"{heading}("
        )
        for heading in normalized_headings
    )


def split_inline_heading(
    text: str,
    headings: set[str],
    *,
    allow_whitespace_separator: bool = False,
) -> tuple[str, str] | None:
    """
    하나의 블록에 붙어 있는 섹션 제목과 본문을 분리한다.

    기본적으로 제목과 본문 사이에 구분 기호가 있어야 한다.
    allow_whitespace_separator가 True이면 공백만 있는 경우도 허용한다.
    """
    heading_pattern = "|".join(
        re.escape(heading).replace(
            r"\ ",
            r"\s*",
        )
        for heading in sorted(
            headings,
            key=len,
            reverse=True,
        )
    )

    if allow_whitespace_separator:
        separator_pattern = (
            r"(?:\s*[:：\-–—]\s*|\s+)"
        )
    else:
        separator_pattern = (
            r"\s*[:：\-–—]\s*"
        )

    match = re.match(
        rf"^\s*(?:\d+[.)]|[가-힣][.)]|\([0-9가-힣]+\))?\s*"
        rf"(?P<heading>{heading_pattern})"
        rf"{separator_pattern}"
        rf"(?P<body>.+)$",
        text,
        flags=re.DOTALL,
    )

    if match is None:
        return None

    heading = match.group("heading").strip()
    body = match.group("body").strip()

    if not body:
        return None

    return heading, body


def find_embedded_boundary_start(
    text: str,
    boundary_patterns: Sequence[re.Pattern[str]],
) -> int | None:
    """
    한 텍스트 블록 안에 붙어 있는 다음 섹션 제목의 시작 위치를 찾는다.

    블록 맨 앞의 제목은 즉시 경계로 인정한다. 문장 중간의 제목은
    앞 문장이 문장부호로 끝난 경우에만 경계로 인정하여,
    일반 본문에 언급된 섹션명을 잘못 자르는 일을 방지한다.
    """
    earliest_start: int | None = None

    for pattern in boundary_patterns:
        for match in pattern.finditer(text):
            prefix = text[:match.start()].rstrip()

            if (
                prefix
                and not prefix.endswith(
                    _SENTENCE_ENDINGS
                )
            ):
                continue

            if (
                earliest_start is None
                or match.start() < earliest_start
            ):
                earliest_start = match.start()

            break

    return earliest_start


def split_before_next_section(
    text: str,
    boundary_patterns: Sequence[re.Pattern[str]],
) -> tuple[str, bool]:
    boundary_start = find_embedded_boundary_start(
        text,
        boundary_patterns,
    )

    if boundary_start is None:
        return text.strip(), False

    return text[:boundary_start].strip(), True


def is_section_boundary_heading(
    text: str,
    boundary_patterns: Sequence[re.Pattern[str]],
    *,
    max_heading_length: int = 120,
) -> bool:
    """
    텍스트 블록 전체가 다음 섹션 제목인지 확인한다.
    """
    cleaned = strip_number_prefix(text).strip()
    normalized = normalize_heading(cleaned)

    if len(normalized) > max_heading_length:
        return False

    return any(
        pattern.fullmatch(cleaned)
        for pattern in boundary_patterns
    )


def collect_section_body(
    elements: list[Tag],
    heading_index: int,
    first_body: str | None,
    boundary_patterns: Sequence[re.Pattern[str]],
    *,
    max_heading_length: int = 120,
) -> str:
    """
    섹션 제목 다음부터 다음 섹션 경계 전까지의 본문을 수집한다.
    """
    body_blocks: list[str] = []

    if first_body:
        first_text, boundary_found = (
            split_before_next_section(
                first_body,
                boundary_patterns,
            )
        )

        if first_text:
            body_blocks.append(first_text)

        if boundary_found:
            return join_text_blocks(
                body_blocks
            )

    for element in elements[
        heading_index + 1:
    ]:
        text = element.get_text(
            " ",
            strip=True,
        )

        if not text:
            continue

        if is_section_boundary_heading(
            text,
            boundary_patterns,
            max_heading_length=max_heading_length,
        ):
            break

        current_text, boundary_found = (
            split_before_next_section(
                text,
                boundary_patterns,
            )
        )

        if current_text:
            body_blocks.append(
                current_text
            )

        if boundary_found:
            break

    return join_text_blocks(body_blocks)