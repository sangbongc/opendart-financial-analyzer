from analysis.income_tax_note_service import (
    IncomeTaxNoteAnalysisError,
    get_income_tax_note_by_corporation,
)
from utils import (
    format_amount,
    pad,
)
from dart.disclosure_service import (
    DisclosureSearchError,
)


def handle_income_tax_note(
    select_corporation,
) -> None:
    """
    선택한 기업의 법인세비용 주요 구성항목을 조회한다.
    """
    print()
    print("[법인세비용 주석 조회]")
    print("-" * 80)

    corporation = select_corporation()

    if corporation is None:
        return

    bsns_year = input(
        "사업연도를 입력하세요: "
    ).strip()

    if (
        len(bsns_year) != 4
        or not bsns_year.isdigit()
    ):
        print(
            "사업연도는 4자리 숫자로 입력해야 합니다."
        )
        return

    fs_div = _input_fs_div()

    if fs_div is None:
        return

    corp_code = str(
        corporation["corp_code"]
    )
    corp_name = str(
        corporation["corp_name"]
    )

    print()
    print(
        f"{corp_name}의 법인세비용 주석을 조회합니다."
    )

    try:
        results = get_income_tax_note_by_corporation(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code="11011",
            fs_div=fs_div,
        )

    except (
        IncomeTaxNoteAnalysisError,
        DisclosureSearchError,
    ) as error:
        print(
            f"법인세비용 주석 조회에 실패했습니다: "
            f"{error}"
        )
        return

    except Exception as error:
        print(
            "예상하지 못한 오류가 발생했습니다: "
            f"{error}"
        )
        return

    if not results:
        print(
            "조회된 법인세비용 구성항목이 없습니다."
        )
        return

    _print_income_tax_note_results(
        corp_name=corp_name,
        bsns_year=bsns_year,
        fs_div=fs_div,
        results=results,
    )


def _input_fs_div() -> str | None:
    """
    연결 또는 별도재무제표 구분을 입력받는다.
    """
    raw_value = input(
        "재무제표 구분을 입력하세요 "
        "[CFS: 연결, OFS: 별도, 기본 CFS]: "
    ).strip().upper()

    fs_div = raw_value or "CFS"

    if fs_div not in {"CFS", "OFS"}:
        print(
            "재무제표 구분은 CFS 또는 OFS여야 합니다."
        )
        return None

    return fs_div


def _print_income_tax_note_results(
    corp_name: str,
    bsns_year: str,
    fs_div: str,
    results,
) -> None:
    statement_name = (
        "연결재무제표"
        if fs_div == "CFS"
        else "별도재무제표"
    )

    print()
    print("[법인세비용 주요 구성항목]")
    print("-" * 100)
    print(f"기업명: {corp_name}")
    print(f"사업연도: {bsns_year}")
    print(f"재무제표 구분: {statement_name}")
    print("-" * 100)

    name_width = 62
    amount_width = 24

    for item in results:
        label = (
            item.label
            or item.local_name
        )

        indent = "    " * item.depth
        display_name = f"{indent}{label}"

        amount = format_amount(
            item.value
        )

        print(
            f"{pad(display_name, name_width)}"
            f"{amount:>{amount_width}}"
        )