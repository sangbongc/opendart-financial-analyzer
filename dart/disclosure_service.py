from typing import Any

from dart.client import DartClient


class DisclosureSearchError(Exception):
    """
    공시 목록 조회에 실패했을 때 발생한다.
    """


REPORT_INFO = {
    "11011": {
        "report_name": "사업보고서",
        "report_month": "12",
    },
    "11012": {
        "report_name": "반기보고서",
        "report_month": "06",
    },
    "11013": {
        "report_name": "분기보고서",
        "report_month": "03",
    },
    "11014": {
        "report_name": "분기보고서",
        "report_month": "09",
    },
}


def find_financial_report_rcept_no(
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
) -> str | None:
    """
    기업, 사업연도, 보고서 코드에 해당하는
    정기공시의 접수번호를 조회한다.
    """
    if not corp_code.strip():
        raise ValueError(
            "기업 고유번호를 입력해야 합니다."
        )

    if not bsns_year.strip():
        raise ValueError(
            "사업연도를 입력해야 합니다."
        )

    if reprt_code not in REPORT_INFO:
        raise ValueError(
            f"지원하지 않는 보고서 코드입니다: {reprt_code}"
        )

    client = DartClient()

    try:
        response = client.get(
            "/list.json",
            {
                "corp_code": corp_code,
                "bgn_de": f"{bsns_year}0101",
                "end_de": f"{int(bsns_year) + 1}1231",
                "pblntf_ty": "A",
                "page_count": "100",
            },
        )

    except Exception as error:
        raise DisclosureSearchError(
            f"공시 목록 조회에 실패했습니다: {error}"
        ) from error

    status = response.get("status")

    if status == "013":
        return None

    if status != "000":
        message = response.get(
            "message",
            "알 수 없는 오류",
        )

        raise DisclosureSearchError(
            f"공시 목록 조회 오류: {message}"
        )

    disclosures = response.get("list", [])

    matched_disclosures = [
        item
        for item in disclosures
        if _matches_financial_report(
            item=item,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
        )
    ]

    if not matched_disclosures:
        return None

    latest_disclosure = max(
        matched_disclosures,
        key=lambda item: str(
            item.get("rcept_dt") or ""
        ),
    )

    rcept_no = latest_disclosure.get("rcept_no")

    if not rcept_no:
        return None

    return str(rcept_no)


def _matches_financial_report(
    item: dict[str, Any],
    bsns_year: str,
    reprt_code: str,
) -> bool:
    """
    조회된 공시가 요청한 사업연도와 보고서 코드에
    해당하는 정기보고서인지 확인한다.
    """
    report_info = REPORT_INFO.get(reprt_code)

    if report_info is None:
        raise ValueError(
            f"지원하지 않는 보고서 코드입니다: {reprt_code}"
        )

    report_nm = str(
        item.get("report_nm") or ""
    ).replace(" ", "")

    expected_name = (
        f"{report_info['report_name']}"
        f"({bsns_year}.{report_info['report_month']})"
        .replace(" ", "")
    )

    return expected_name in report_nm