import re
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
    allowed_names = {
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
        "title",
        "tu",
        "te",
    }

    candidates = soup.find_all(
        lambda tag: (
            isinstance(tag, Tag)
            and tag.name
            and tag.name.lower()
            in allowed_names
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
                in allowed_names
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