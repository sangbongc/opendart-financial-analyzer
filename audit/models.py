from dataclasses import dataclass

@dataclass(frozen=True)
class KeyAuditMatter:
    """
    감사보고서에서 추출한 개별 핵심감사사항.
    """

    title: str | None
    text: str


@dataclass(frozen=True)
class KeyAuditMatters:
    """
    감사보고서의 핵심감사사항 섹션 전체 결과.
    """

    heading: str
    introduction_text: str | None
    matters: tuple[KeyAuditMatter, ...]