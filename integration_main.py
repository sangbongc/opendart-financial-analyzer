from analysis.income_tax_note_service import (
    get_major_components_of_tax_expense,
    get_income_tax_note_by_corporation,
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
    results = get_income_tax_note_by_corporation(
        corp_code="00126380",
        bsns_year="2025",
    )

    print("[법인세비용 구성표]")
    print("-" * 120)
    for item in results:
        print(
            item.depth,
            item.label,
            item.value,
        )

if __name__ == "__main__":
    main()