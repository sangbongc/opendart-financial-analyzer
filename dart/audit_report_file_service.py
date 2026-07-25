from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode

import requests

from dart.client import DartAPIError, DartClient
from dart.audit_report_viewer_parser import (
    build_viewer_url,
    extract_attachment_viewer_urls,
    to_int,
    AuditReportAttachment,
)

DART_MAIN_URL = "https://dart.fss.or.kr/dsaf001/main.do"

DEFAULT_TIMEOUT = 30
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


class AuditReportFileError(Exception):
    """감사보고서 공시 검색 또는 원문 다운로드 오류."""


@dataclass(frozen=True)
class AuditReportDisclosure:
    corp_code: str
    corp_name: str
    report_name: str
    rcept_no: str
    rcept_date: str
    filer_name: str





@dataclass(frozen=True)
class _ViewerSection:
    ele_id: int
    url: str
    html: str




class _AttachmentOptionParser(HTMLParser):
    """첨부문서 선택 상자의 option 값을 추출한다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.options: list[tuple[str, str]] = []
        self._inside_select = False
        self._value: str | None = None
        self._text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        tag = tag.lower()

        if tag == "select":
            self._inside_select = attributes.get("id") == "att"
        elif self._inside_select and tag == "option":
            value = str(attributes.get("value") or "").strip()
            if value and value != "null":
                self._value = value
                self._text = []

    def handle_data(self, data: str) -> None:
        if self._value is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "option" and self._value is not None:
            title = " ".join("".join(self._text).split())
            self.options.append((self._value, title))
            self._value = None
            self._text = []
        elif tag == "select" and self._inside_select:
            self._inside_select = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_audit_reports(
    corp_code: str,
    start_date: str,
    end_date: str,
) -> list[AuditReportDisclosure]:
    """조회 기간의 감사보고서 관련 공시를 최신순으로 반환한다."""
    _validate_search_inputs(corp_code, start_date, end_date)

    client = DartClient()
    results: dict[str, AuditReportDisclosure] = {}
    page_no = 1

    while True:
        try:
            response = client.get(
                "/list.json",
                {
                    "corp_code": corp_code,
                    "bgn_de": start_date,
                    "end_de": end_date,
                    "sort": "date",
                    "sort_mth": "desc",
                    "page_no": str(page_no),
                    "page_count": "100",
                },
            )
        except DartAPIError as error:
            if getattr(error, "status", None) == "013":
                break
            raise AuditReportFileError(
                "감사보고서 제출 공시 검색에 실패했습니다."
            ) from error

        items = list(response.get("list", []))
        for item in items:
            report_name = str(
                item.get("report_nm") or ""
            ).strip()

            rcept_date = str(
                item.get("rcept_dt") or ""
            )
            rcept_no = str(
                item.get("rcept_no") or ""
            )

            is_audit_report = (
                _is_audit_report_related_disclosure(
                    report_name
                )
            )


            if not is_audit_report:
                continue

            disclosure = AuditReportDisclosure(
                corp_code=str(
                    item.get("corp_code") or ""
                ),
                corp_name=str(
                    item.get("corp_name") or ""
                ),
                report_name=report_name,
                rcept_no=rcept_no,
                rcept_date=rcept_date,
                filer_name=str(
                    item.get("flr_nm") or ""
                ),
            )

            results[
                disclosure.rcept_no
            ] = disclosure

        if (
            not items
            or page_no >= to_int(
                response.get("total_page"),
                1,
            )
        ):
            break

        page_no += 1

    return sorted(
        results.values(),
        key=lambda item: (item.rcept_date, item.rcept_no),
        reverse=True,
    )


def select_latest_audit_report(
    disclosures: list[AuditReportDisclosure],
) -> AuditReportDisclosure:
    """검색 결과에서 가장 최근 공시를 선택한다."""
    if not disclosures:
        raise AuditReportFileError(
            "조회 기간에 감사보고서 제출 공시가 없습니다."
        )
    return max(
        disclosures,
        key=lambda item: (item.rcept_date, item.rcept_no),
    )


def fetch_audit_report_attachments(
    rcept_no: str,
    timeout: int = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> list[AuditReportAttachment]:
    """공시 메인 페이지에서 감사보고서 첨부문서를 찾는다."""
    _validate_rcept_no(rcept_no)

    request_session = session or requests.Session()
    request_session.headers.update(DEFAULT_HEADERS)

    response = request_session.get(
        DART_MAIN_URL,
        params={"rcpNo": rcept_no},
        timeout=timeout,
    )
    response.raise_for_status()

    candidates = _extract_attachment_candidates(response.text, rcept_no)
    if not candidates:
        raise AuditReportFileError(
            "공시 페이지에서 감사보고서 문서번호를 찾지 못했습니다. "
            f"rcept_no={rcept_no}"
        )

    unique = {
        (item.dcm_no, item.is_consolidated): item
        for item in candidates
    }
    return sorted(
        unique.values(),
        key=lambda item: (not item.is_consolidated, item.title),
    )


def select_audit_report_attachment(
    attachments: list[AuditReportAttachment],
    consolidated: bool | None,
) -> AuditReportAttachment:
    """별도·연결 조건에 맞는 첨부문서를 선택한다."""
    if not attachments:
        raise AuditReportFileError(
            "선택할 감사보고서 문서가 없습니다."
        )

    if consolidated is None:
        return next(
            (item for item in attachments if item.is_consolidated),
            attachments[0],
        )

    matched = next(
        (
            item
            for item in attachments
            if item.is_consolidated is consolidated
        ),
        None,
    )
    if matched is not None:
        return matched

    report_type = "연결" if consolidated else "별도"
    names = ", ".join(item.title for item in attachments)
    raise AuditReportFileError(
        f"첨부문서에서 {report_type}감사보고서를 찾지 못했습니다. "
        f"확인된 문서: {names}"
    )


def download_audit_report_attachment(
    attachment: AuditReportAttachment,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """감사보고서 viewer 조각을 내려받아 하나의 HTML로 병합한다."""
    main_url = (
        f"{DART_MAIN_URL}?rcpNo={attachment.rcept_no}"
        f"&dcmNo={attachment.dcm_no}"
    )
    sections = _download_viewer_sections(
        attachment=attachment,
        main_url=main_url,
        timeout=timeout,
    )

    if not sections:
        raise AuditReportFileError(
            "감사보고서 조각을 내려받았지만 내용이 비어 있습니다. "
            f"문서명='{attachment.title}', dcmNo={attachment.dcm_no}"
        )

    document = _combine_viewer_sections(sections, attachment)
    if not _looks_like_audit_report_body(_strip_html(document)):
        raise AuditReportFileError(
            "병합한 문서에서 감사보고서 본문을 확인하지 못했습니다. "
            f"문서명='{attachment.title}', "
            f"dcmNo={attachment.dcm_no}, "
            f"조각 수={len(sections)}"
        )

    return normalize_html_charset(document)


def fetch_latest_audit_report_text(
    corp_code: str,
    start_date: str,
    end_date: str,
    consolidated: bool | None = None,
) -> str:
    """공시 검색부터 최신 감사보고서 본문 반환까지 수행한다."""
    disclosure = select_latest_audit_report(
        search_audit_reports(corp_code, start_date, end_date)
    )
    attachment = select_audit_report_attachment(
        fetch_audit_report_attachments(disclosure.rcept_no),
        consolidated,
    )
    return download_audit_report_attachment(attachment)


# ---------------------------------------------------------------------------
# Download and viewer parsing
# ---------------------------------------------------------------------------


def _download_viewer_sections(
    attachment: AuditReportAttachment,
    main_url: str,
    timeout: int,
) -> list[_ViewerSection]:
    try:
        from playwright.sync_api import (
            TimeoutError as PlaywrightTimeoutError,
        )
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise AuditReportFileError(
            "감사보고서 원문 다운로드에는 Playwright가 필요합니다. "
            "'pip install playwright'와 "
            "'playwright install chromium'을 실행하세요."
        ) from error

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                locale="ko-KR",
                user_agent=DEFAULT_HEADERS["User-Agent"],
            )
            page = context.new_page()
            page.goto(
                main_url,
                wait_until="domcontentloaded",
                timeout=timeout * 1000,
            )
            page.wait_for_timeout(1500)

            viewer_urls = extract_attachment_viewer_urls(
                page.content(),
                attachment,
            )
            if not viewer_urls:
                raise AuditReportFileError(
                    "첨부문서 페이지에서 감사보고서 조각 URL을 "
                    "찾지 못했습니다. "
                    f"dcmNo={attachment.dcm_no}"
                )

            sections: list[_ViewerSection] = []
            for ele_id, viewer_url in viewer_urls:
                response = context.request.get(
                    viewer_url,
                    headers={"Referer": main_url},
                    timeout=timeout * 1000,
                )
                if not response.ok:
                    raise AuditReportFileError(
                        "감사보고서 조각 다운로드에 실패했습니다. "
                        f"eleId={ele_id}, status={response.status}"
                    )

                section_html = _decode_dart_html_response(
                    response.body(),
                    response.headers,
                )
                if section_html.strip():
                    sections.append(
                        _ViewerSection(
                            ele_id=to_int(ele_id, 0),
                            url=viewer_url,
                            html=section_html,
                        )
                    )

            return sorted(sections, key=lambda item: item.ele_id)

    except PlaywrightTimeoutError as error:
        raise AuditReportFileError(
            "DART 감사보고서 페이지 렌더링 시간이 초과되었습니다. "
            f"rcept_no={attachment.rcept_no}, "
            f"dcmNo={attachment.dcm_no}"
        ) from error
    except AuditReportFileError:
        raise
    except Exception as error:
        raise AuditReportFileError(
            "DART 감사보고서 렌더링 중 오류가 발생했습니다. "
            f"rcept_no={attachment.rcept_no}, "
            f"dcmNo={attachment.dcm_no}: {error}"
        ) from error


def _combine_viewer_sections(
    sections: list[_ViewerSection],
    attachment: AuditReportAttachment,
) -> str:
    body_parts: list[str] = []

    for section in sections:
        match = re.search(
            r"<body\b[^>]*>(.*?)</body>",
            section.html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        body = match.group(1) if match else section.html
        body_parts.append(
            f'<section data-ele-id="{section.ele_id}" '
            f'data-source-url="{html.escape(section.url)}">\n'
            f"{body}\n</section>"
        )

    title = html.escape(attachment.title)
    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="ko">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{title}</title>",
            "</head>",
            "<body>",
            *body_parts,
            "</body>",
            "</html>",
        ]
    )


# ---------------------------------------------------------------------------
# Attachment parsing and validation
# ---------------------------------------------------------------------------


def _extract_attachment_candidates(
    page_text: str,
    rcept_no: str,
) -> list[AuditReportAttachment]:
    parser = _AttachmentOptionParser()
    parser.feed(page_text)

    candidates: list[AuditReportAttachment] = []
    for value, raw_title in parser.options:
        parameters = parse_qs(value)
        dcm_no = parameters.get("dcmNo", [""])[0].strip()
        if not dcm_no or not _is_audit_report_title(raw_title):
            continue

        candidates.append(
            AuditReportAttachment(
                title=_clean_title(raw_title),
                rcept_no=(
                    parameters.get("rcpNo", [rcept_no])[0].strip()
                    or rcept_no
                ),
                dcm_no=dcm_no,
            )
        )

    return candidates


def _is_audit_report_related_disclosure(
    report_name: str,
) -> bool:
    normalized = re.sub(
        r"\s+",
        "",
        report_name,
    )

    return (
        "감사보고서" in normalized
        or "사업보고서" in normalized
    )

def _is_audit_report_title(title: str) -> bool:
    normalized = "".join(html.unescape(title).split())
    excluded = (
        "영문감사보고서",
        "감사의감사보고서",
        "감사의의견서",
        "내부감시장치",
        "내부회계관리제도",
    )
    return (
        normalized.endswith("감사보고서")
        and not any(keyword in normalized for keyword in excluded)
    )


def _clean_title(title: str) -> str:
    normalized = " ".join(html.unescape(title).split())
    if "연결감사보고서" in normalized:
        return "연결감사보고서"
    if "감사보고서" in normalized:
        return "감사보고서"
    return normalized


def _looks_like_audit_report_body(text: str) -> bool:
    normalized = "".join(text.split())
    has_title = any(
        marker in normalized
        for marker in (
            "독립된감사인의감사보고서",
            "독립된감사인의연결감사보고서",
        )
    )
    has_section = any(
        marker in normalized
        for marker in (
            "감사의견",
            "감사의견근거",
            "재무제표에대한경영진",
            "재무제표감사에대한감사인의책임",
            "감사인의책임",
        )
    )
    return has_title and has_section


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _decode_dart_html_response(
    content: bytes,
    headers: dict[str, str],
) -> str:
    content_type = str(headers.get("content-type") or "")
    match = re.search(
        r"charset\s*=\s*['\"]?([^;\s'\"]+)",
        content_type,
        flags=re.IGNORECASE,
    )
    encodings = [match.group(1)] if match else []
    encodings.extend(("utf-8", "cp949", "euc-kr"))

    for encoding in dict.fromkeys(encodings):
        try:
            return content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            pass
    return content.decode("utf-8", errors="replace")


def _strip_html(content: str) -> str:
    content = re.sub(
        r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>",
        " ",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    content = re.sub(r"<[^>]+>", " ", content)
    return " ".join(html.unescape(content).split())


def _validate_search_inputs(
    corp_code: str,
    start_date: str,
    end_date: str,
) -> None:
    if len(corp_code) != 8 or not corp_code.isdigit():
        raise ValueError("기업 고유번호는 숫자 8자리여야 합니다.")

    for label, value in (("시작일", start_date), ("종료일", end_date)):
        if len(value) != 8 or not value.isdigit():
            raise ValueError(f"{label}은 YYYYMMDD 형식이어야 합니다.")

    if start_date > end_date:
        raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")


def _validate_rcept_no(rcept_no: str) -> None:
    if len(rcept_no) != 14 or not rcept_no.isdigit():
        raise ValueError("접수번호는 숫자 14자리여야 합니다.")




def normalize_html_charset(content: str) -> str:
    content = re.sub(
        r'(?i)<meta[^>]+charset\s*=\s*["\']?[^"\'>\s]+["\']?[^>]*>',
        '<meta charset="utf-8">',
        content,
        count=1,
    )
    content = re.sub(
        r'(?i)<meta[^>]+http-equiv\s*=\s*["\']content-type["\'][^>]*>',
        '<meta charset="utf-8">',
        content,
        count=1,
    )
    if not re.search(r'(?i)<meta[^>]+charset=', content):
        content = re.sub(
            r"(?i)<head[^>]*>",
            lambda match: match.group(0) + '\n<meta charset="utf-8">',
            content,
            count=1,
        )
    return content