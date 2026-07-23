
from dataclasses import dataclass

from bs4 import BeautifulSoup




@dataclass(frozen=True)
class AuditReportDocument:
    document_code: str
    document_name: str
    company_name: str
    company_code: str | None
    xml_text: str


def parse_audit_report_document(
    xml_text: str,
) -> AuditReportDocument:
    soup = BeautifulSoup(
        xml_text,
        "xml",
    )

    document_name_tag = soup.find("DOCUMENT-NAME")
    company_name_tag = soup.find("COMPANY-NAME")

    if document_name_tag is None:
        raise ValueError(
            "DOCUMENT-NAME 태그를 찾을 수 없습니다."
        )

    if company_name_tag is None:
        raise ValueError(
            "COMPANY-NAME 태그를 찾을 수 없습니다."
        )

    document_code = document_name_tag.get("ACODE")

    if not document_code:
        raise ValueError(
            "DOCUMENT-NAME의 ACODE를 찾을 수 없습니다."
        )

    document_name = document_name_tag.get_text(
        strip=True,
    )
    company_name = company_name_tag.get_text(
        strip=True,
    )
    company_code = company_name_tag.get("AREGCIK")

    return AuditReportDocument(
        document_code=document_code,
        document_name=document_name,
        company_name=company_name,
        company_code=company_code,
        xml_text=xml_text,
    )