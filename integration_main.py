import os
from bs4 import BeautifulSoup


from audit.audit_report_parser import (
    parse_audit_report_document,
)
from dart.audit_report_file_service import (
    download_audit_report_zip,
    list_document_files,
    read_document_text,
    save_audit_report_zip,
)
from audit.audit_opinion_parser import (
    parse_audit_opinion,
)


def inspect_audit_opinion_structure(
    xml_text: str,
) -> None:
    soup = BeautifulSoup(
        xml_text,
        "xml",
    )

    matches = soup.find_all(
        string=lambda text: (
            text
            and "감사의견" in " ".join(text.split())
        )
    )

    print()
    print("[감사의견 XML 구조]")
    print("-" * 60)

    for index, text_node in enumerate(
        matches,
        start=1,
    ):
        parent = text_node.parent

        print()
        print(f"{index}. 텍스트: {text_node.strip()}")
        print(f"태그명: {parent.name}")
        print(f"속성: {dict(parent.attrs)}")
        print("태그 원문:")
        print(str(parent)[:1000])

def main() -> None:
    rcept_no = "20260310002820"

    api_key = os.getenv("crtfc_key")

    if not api_key:
        raise RuntimeError(
            "DART_API_KEY 환경변수가 설정되지 않았습니다."
        )

    zip_content = download_audit_report_zip(
        rcept_no=rcept_no,
        api_key=api_key,
    )

    save_path = save_audit_report_zip(
        zip_content=zip_content,
        rcept_no=rcept_no,
        output_dir="data/audit_reports",
    )

    print(f"ZIP 저장 경로: {save_path}")

    filenames = list_document_files(
        zip_content=zip_content,
    )

    print()
    print("[감사보고서 문서 파싱 결과]")
    print("-" * 60)

    for filename in filenames:
        if not filename.lower().endswith(".xml"):
            continue

        document_text = read_document_text(
            zip_content=zip_content,
            filename=filename,
        )

        document = parse_audit_report_document(
            xml_text=document_text,
        )

        print(
            f"확인 중: {filename} "
            f"({document.document_code})"
        )

        if document.document_code != "00761":
            continue

        audit_opinion = parse_audit_opinion(
            xml_text=document_text,
        )

        print()
        print("[감사의견 파싱 결과]")
        print("-" * 60)
        print(f"문서명: {document.document_name}")
        print(f"단락 제목: {audit_opinion.heading}")
        print(f"의견 유형: {audit_opinion.opinion_type}")
        print()
        print(audit_opinion.opinion_text)

if __name__ == "__main__":
    main()