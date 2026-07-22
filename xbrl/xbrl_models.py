from __future__ import annotations
from dataclasses import dataclass

from xbrl.xbrl_utils import(
    get_qname_local_name,
)


@dataclass(frozen=True)
class XbrlDimensionMember:
    """
    XBRL context에 포함된 하나의 차원과 Member를 나타낸다.
    """

    dimension: str
    member: str

    @property
    def dimension_local_name(self) -> str:
        return get_qname_local_name(
            self.dimension
        )

    @property
    def member_local_name(self) -> str:
        return get_qname_local_name(
            self.member
        )


@dataclass(frozen=True)
class XbrlContext:
    """
    XBRL Fact가 어떤 기간과 차원에 해당하는지 나타낸다.
    """

    context_id: str
    entity_identifier: str | None

    start_date: str | None
    end_date: str | None
    instant_date: str | None

    dimensions: tuple[
        XbrlDimensionMember,
        ...,
    ]

    @property
    def member_local_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            dimension.member_local_name
            for dimension in self.dimensions
        )

    def has_member(
        self,
        member_local_name: str,
    ) -> bool:
        return member_local_name in (
            self.member_local_names
        )

    @property
    def is_duration(self) -> bool:
        return (
            self.start_date is not None
            and self.end_date is not None
        )

    @property
    def is_instant(self) -> bool:
        return self.instant_date is not None


@dataclass(frozen=True)
class PresentationConcept:
    concept_id: str
    local_name: str
    locator_label: str
    href: str
    parent_concept_id: str | None
    depth: int
    order: float
    has_children: bool


@dataclass(frozen=True)
class XbrlFact:
    """
    XBRL 인스턴스에서 추출한 하나의 Fact를 나타낸다.
    """

    concept_id: str
    local_name: str
    namespace_uri: str

    value: str | None

    context_ref: str
    context: XbrlContext | None

    unit_ref: str | None
    decimals: str | None

    is_nil: bool


@dataclass(frozen=True)
class NoteTableItem:
    """
    주석 표의 표시 구조와 실제 Fact 목록을 함께 보관한다.
    """

    concept: PresentationConcept
    facts: tuple[XbrlFact, ...]


@dataclass(frozen=True)
class XbrlLabel:
    concept_id: str
    text: str
    language: str | None
    role: str | None