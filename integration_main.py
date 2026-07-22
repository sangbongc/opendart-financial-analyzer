from analysis.income_tax_note_service import (
    get_major_components_of_tax_expense,
)
from dart.xbrl_file_service import (
    download_xbrl_archive,
)


TAX_NOTE_CONSOLIDATED_ROLE_URI = (
    "http://dart.fss.or.kr/role/ifrs/"
    "ias_12_role-D835110"
)

MAJOR_TAX_COMPONENTS_TABLE = (
    "MajorComponentsOfTaxExpenseIncomeTable"
)

def get_presentation_concept_type(
    local_name: str,
) -> str:
    if local_name.endswith("Table"):
        return "TABLE"

    if local_name.endswith("Axis"):
        return "AXIS"

    if local_name.endswith("Domain"):
        return "DOMAIN"

    if local_name.endswith("Member"):
        return "MEMBER"

    if local_name.endswith("LineItems"):
        return "LINE_ITEMS"

    if local_name.endswith("Abstract"):
        return "ABSTRACT"

    if local_name.endswith("Explanatory"):
        return "EXPLANATORY"

    if local_name.endswith("TextBlock"):
        return "TEXT_BLOCK"

    return "FACT"


def main() -> None:
    content = download_xbrl_archive(
        rcept_no="20260310002820",
        reprt_code="11011",
    )

    print("[법인세비용 구성표]")
    print("-" * 120)
    results = get_major_components_of_tax_expense(
        content=content,
        bsns_year="2025",
        fs_div="CFS",
    )

    for result in results:
        indent = "    " * result.depth

        if result.value is None:
            formatted_value = "-"
        else:
            formatted_value = f"{result.value:,.0f}"

        display_name = (
            result.label
            if result.label
            else result.local_name
        )

        print(
            f"{indent}"
            f"- {display_name}: "
            f"{formatted_value}"
        )
    # for item in items:
    #     concept = item.concept
    #     indent = "    " * concept.depth

    #     print(
    #         f"{indent}"
    #         f"- {concept.local_name}"
    #     )

    #     if not item.facts:
    #         print(
    #             f"{indent}"
    #             f"    Fact 없음"
    #         )
    #         continue

    #     for fact in item.facts:
    #         print(
    #             f"{indent}"
    #             f"    값={fact.value} / "
    #             f"context={fact.context_ref} / "
    #             f"unit={fact.unit_ref} / "
    #             f"decimals={fact.decimals}"
    #         )
    
    # for item in items:
    #     concept = item.concept
    #     indent = "    " * concept.depth

    #     print(
    #         f"{indent}"
    #         f"- {concept.local_name}"
    #     )

    #     for fact in item.facts:
    #         context = fact.context

    #         if context is None:
    #             print(
    #                 f"{indent}"
    #                 f"    값={fact.value} / "
    #                 f"context 파싱 실패"
    #             )
    #             continue

    #         members = ", ".join(
    #             context.member_local_names
    #         )

    #         period = (
    #             f"{context.start_date}"
    #             f" ~ {context.end_date}"
    #             if context.is_duration
    #             else context.instant_date
    #         )

    #         print(
    #             f"{indent}"
    #             f"    값={fact.value} / "
    #             f"기간={period} / "
    #             f"members=[{members}]"
    #         )

if __name__ == "__main__":
    main()