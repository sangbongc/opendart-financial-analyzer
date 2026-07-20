from console.corporation_selector import(
    select_corporation,
)
from console.commands.corporation_commands import(
    input_financial_statement_conditions,
)
from dart.financial_statement_service import(
    sync_financial_statements,
)
from database.financial_statement_repository import(
    fetch_financial_statements_from_db,
)

from utils import (
    pad,
    format_amount,
)


def handle_sync_financial_statements() -> None:
        """
        기업과 보고서 조건을 입력받아
        DART 재무제표를 수집하고 DB에 저장한다.
        """
        corporation = select_corporation()

        if corporation is None:
            return

        conditions = (
            input_financial_statement_conditions()
        )

        print("\n[재무제표 수집 조건]")
        print("-" * 60)
        print(f"기업명: {corporation['corp_name']}")
        print(f"고유번호: {corporation['corp_code']}")
        print(f"사업연도: {conditions['bsns_year']}")
        print(f"보고서 코드: {conditions['reprt_code']}")
        print(f"재무제표 구분: {conditions['fs_div']}")

        print("\n재무제표 수집을 시작합니다.")

        try:
            result = sync_financial_statements(
                corp_code=corporation["corp_code"],
                bsns_year=conditions["bsns_year"],
                reprt_code=conditions["reprt_code"],
                fs_div=conditions["fs_div"],
            )

        except Exception as error:
            print(
                "재무제표 동기화 중 예상하지 못한 "
                f"오류가 발생했습니다: {error}"
            )
            return

        print("\n재무제표 동기화 완료")
        print("-" * 60)
        print(f"수신 행 수: {result['received_count']:,}")
        print(f"저장 행 수: {result['saved_count']:,}")

        duplicate_count = result.get(
            "duplicate_count",
            result["received_count"] - result["saved_count"],
        )

        print(f"중복 제외: {duplicate_count:,}")


def handle_view_financial_statements() -> None:
        """
        데이터베이스에 저장된 재무제표를 조회하고 출력한다.
        """
        print("\n[저장된 재무제표 조회]")
        print("-" * 60)

        try:
            corporation = select_corporation(
            )

        except Exception as error:
            print(f"기업 조회 중 오류가 발생했습니다: {error}")
            return

        if corporation is None:
            print("일치하는 기업을 찾지 못했습니다.")
            return

        corp_code = corporation["corp_code"]
        corp_name = corporation["corp_name"]

        bsns_year = input(
            "사업연도를 입력하세요: "
        ).strip()

        if not bsns_year:
            print("사업연도를 입력해야 합니다.")
            return

        if not (
            len(bsns_year) == 4
            and bsns_year.isdigit()
        ):
            print("사업연도는 4자리 숫자로 입력해야 합니다.")
            return

        reprt_code = input(
            "보고서 코드를 입력하세요 "
            "(기본값: 11011): "
        ).strip()

        if not reprt_code:
            reprt_code = "11011"

        fs_div = input(
            "재무제표 구분을 입력하세요 "
            "(CFS/OFS, 기본값: CFS): "
        ).strip().upper()

        if not fs_div:
            fs_div = "CFS"

        if fs_div not in {"CFS", "OFS"}:
            print("재무제표 구분은 CFS 또는 OFS여야 합니다.")
            return

        sj_div_input = input(
            "재무제표 종류를 입력하세요 "
            "(BS/IS/CIS/CF/전체, 기본값: 전체): "
        ).strip().upper()

        sj_div: str | None

        if not sj_div_input or sj_div_input in {
            "전체",
            "ALL",
        }:
            sj_div = None

        elif sj_div_input in {
            "BS",
            "IS",
            "CIS",
            "CF",
        }:
            sj_div = sj_div_input

        else:
            print(
                "재무제표 종류는 "
                "BS, IS, CIS, CF 또는 전체여야 합니다."
            )
            return

        try:
            rows = fetch_financial_statements_from_db(
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
                sj_div=sj_div,
            )

        except Exception as error:
            print(
                "재무제표 조회 중 오류가 발생했습니다: "
                f"{error}"
            )
            return

        if not rows:
            print("\n조회된 재무제표가 없습니다.")
            print(
                "먼저 fs 명령으로 재무제표를 "
                "동기화했는지 확인하세요."
            )
            return

        print()
        print(f"기업명: {corp_name}")
        print(f"기업 고유번호: {corp_code}")
        print(f"사업연도: {bsns_year}")
        print(f"보고서 코드: {reprt_code}")
        print(f"재무제표 구분: {fs_div}")

        statement_names = {
            "BS": "재무상태표",
            "IS": "손익계산서",
            "CIS": "포괄손익계산서",
            "CF": "현금흐름표",
            "SCE": "자본변동표",
        }

        grouped_rows: dict[str, list[dict]] = {}

        for row in rows:
            row_sj_div = row["sj_div"]

            if row_sj_div not in grouped_rows:
                grouped_rows[row_sj_div] = []

            grouped_rows[row_sj_div].append(row)

        for statement_code, statement_rows in grouped_rows.items():
            statement_name = statement_names.get(
                statement_code,
                statement_rows[0].get("sj_nm")
                or statement_code,
            )

            print()
            print(
                f"[{statement_name} "
                f"({statement_code})]"
            )
            print("-" * 100)
            print(
                f"{'계정명':<35}"
                f"{'당기 금액':>25}"
                f"{'전기 금액':>25}"
            )
            print("-" * 100)

            for row in statement_rows:
                account_name = (
                    row.get("account_nm")
                    or "-"
                )

                current_amount = (
                    row.get("thstrm_amount")
                )

                previous_amount = (
                    row.get("frmtrm_amount")
                )

                print(
                    f"{pad(account_name, 35)}"
                    f"{format_amount(current_amount):>25}"
                    f"{format_amount(previous_amount):>25}"
                )

            print("-" * 100)
            print(
                f"총 계정 수: "
                f"{len(statement_rows):,}개"
            )
