import html
import re
from urllib.parse import parse_qs, urlencode
from dataclasses import dataclass

DART_VIEWER_URL = "https://dart.fss.or.kr/report/viewer.do"

@dataclass(frozen=True)
class _ViewerReference:
    ele_id: str
    offset: str
    length: str
    dtd: str

@dataclass(frozen=True)
class AuditReportAttachment:
    title: str
    rcept_no: str
    dcm_no: str
    ele_id: str = "0"
    offset: str = "0"
    length: str = "0"
    dtd: str = "HTML"

    @property
    def normalized_title(self) -> str:
        return "".join(self.title.split())

    @property
    def is_consolidated(self) -> bool:
        return "연결감사보고서" in self.normalized_title

    @property
    def viewer_url(self) -> str:
        return build_viewer_url(
            self.rcept_no,
            self.dcm_no,
            self.ele_id,
            self.offset,
            self.length,
            self.dtd,
        )

def _extract_javascript_records(content: str) -> list[dict[str, str]]:
    assignment_pattern = re.compile(
        r"""
        (?P<node>[A-Za-z_$][\w$]*)\s*
        (?:
            \[\s*['"](?P<bracket_key>rcpNo|dcmNo|eleId|offset|length|dtd)['"]\s*\]
            |
            \.\s*(?P<dot_key>rcpNo|dcmNo|eleId|offset|length|dtd)
        )
        \s*=\s*
        (?:
            (?P<quote>['"])(?P<quoted_value>.*?)(?P=quote)
            |
            (?P<bare_value>[^;\s]+)
        )\s*;
        """,
        flags=re.DOTALL | re.IGNORECASE | re.VERBOSE,
    )

    active: dict[str, dict[str, str]] = {}
    completed: list[dict[str, str]] = []

    def flush(node_name: str) -> None:
        record = active.get(node_name)
        if record and record.get("eleId"):
            completed.append(record.copy())
        active[node_name] = {}

    for match in assignment_pattern.finditer(content):
        node_name = match.group("node")
        key = match.group("bracket_key") or match.group("dot_key")
        value = (
            match.group("quoted_value")
            if match.group("quoted_value") is not None
            else match.group("bare_value") or ""
        )
        value = html.unescape(
            value.replace(r"\'", "'")
            .replace(r'\"', '"')
            .replace(r"\\", "\\")
        ).strip()

        record = active.setdefault(node_name, {})
        if key in record:
            flush(node_name)
            record = active.setdefault(node_name, {})
        record[key] = value

    for node_name in list(active):
        flush(node_name)

    return completed


def build_viewer_url(
    rcept_no: str,
    dcm_no: str,
    ele_id: str,
    offset: str,
    length: str,
    dtd: str,
) -> str:
    return f"{DART_VIEWER_URL}?" + urlencode(
        {
            "rcpNo": rcept_no,
            "dcmNo": dcm_no,
            "eleId": ele_id,
            "offset": offset or "0",
            "length": length or "0",
            "dtd": dtd or "HTML",
        }
    )


def to_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default



def _decode_embedded_html(content: str) -> str:
    return (
        html.unescape(content)
        .replace(r"\/", "/")
        .replace(r"\u0026", "&")
        .replace(r"\x26", "&")
    )


def extract_attachment_viewer_urls(
    page_html: str,
    attachment: AuditReportAttachment,
) -> list[tuple[str, str]]:
    decoded = _decode_embedded_html(page_html)
    references: dict[tuple[int, int, int, str], _ViewerReference] = {}

    def add(values: dict[str, str]) -> None:
        rcept_no = values.get("rcpNo", attachment.rcept_no)
        dcm_no = values.get("dcmNo", attachment.dcm_no)
        ele_id = values.get("eleId", "")
        if (
            rcept_no != attachment.rcept_no
            or dcm_no != attachment.dcm_no
            or not ele_id
        ):
            return

        reference = _ViewerReference(
            ele_id=ele_id,
            offset=values.get("offset", "0") or "0",
            length=values.get("length", "0") or "0",
            dtd=values.get("dtd", "HTML") or "HTML",
        )
        key = (
            to_int(reference.ele_id, 0),
            to_int(reference.offset, 0),
            to_int(reference.length, 0),
            reference.dtd,
        )
        references[key] = reference

    for raw_url in re.findall(
        r"(?:https?://dart\.fss\.or\.kr)?"
        r"/report/viewer\.do\?[^\"'<>\s]+",
        decoded,
        flags=re.IGNORECASE,
    ):
        raw_url = raw_url.replace("&amp;", "&")
        parameters = parse_qs(raw_url.split("?", 1)[-1])
        add({key: values[0] for key, values in parameters.items()})

    for values in _extract_javascript_records(decoded):
        add(values)

    function_pattern = re.compile(
        r"(?:viewDoc|viewDoc2|openViewer)\s*\(\s*"
        r"['\"](?P<rcpNo>\d{14})['\"]\s*,\s*"
        r"['\"](?P<dcmNo>\d+)['\"]\s*,\s*"
        r"['\"](?P<eleId>\d+)['\"]\s*,\s*"
        r"['\"](?P<offset>\d+)['\"]\s*,\s*"
        r"['\"](?P<length>\d+)['\"]\s*,\s*"
        r"['\"](?P<dtd>[^'\"]+)['\"]",
        flags=re.IGNORECASE,
    )
    for match in function_pattern.finditer(decoded):
        add(match.groupdict())

    return [
        (
            reference.ele_id,
            build_viewer_url(
                attachment.rcept_no,
                attachment.dcm_no,
                reference.ele_id,
                reference.offset,
                reference.length,
                reference.dtd,
            ),
        )
        for _, reference in sorted(references.items())
    ]