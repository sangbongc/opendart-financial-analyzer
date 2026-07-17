from dart.corporation_service import (
    CorporationSyncError,
    sync_corporations,
    find_corporations,
    find_corporations_with_count
)
from database.corporation_repository import (
    count_corporations,
)
from dart.financial_statement_service import (
    sync_financial_statements,
)
REPORT_CODE_ALIASES = {
    "annual": "11011",
    "a": "11011",
    "사업보고서": "11011",

    "q1": "11013",
    "1q": "11013",
    "1분기": "11013",

    "half": "11012",
    "h": "11012",
    "반기": "11012",

    "q3": "11014",
    "3q": "11014",
    "3분기": "11014",
}

REPORT_CODE_NAMES = {
    "11011": "사업보고서",
    "11013": "1분기보고서",
    "11012": "반기보고서",
    "11014": "3분기보고서",
}

FS_DIV_ALIASES = {
    "cfs": "CFS",
    "연결": "CFS",
    "연결재무제표": "CFS",

    "ofs": "OFS",
    "별도": "OFS",
    "개별": "OFS",
    "별도재무제표": "OFS",
}

class ConsoleController:
    """
    OpenDART Financial Analyzer의 콘솔 입력과
    서비스 호출 흐름을 관리한다.
    """

    def __init__(
        self,
        sync_corporations_on_start: bool = False,
    ) -> None:
        self.sync_corporations_on_start = (
            sync_corporations_on_start
        )

    def run(self) -> None:
        """
        콘솔 프로그램을 실행한다.
        """
        print("=" * 60)
        print("OpenDART Financial Analyzer")
        print("=" * 60)

        if self.sync_corporations_on_start:
            self._initialize_corporations()

        self._print_help()

        while True:
            command = input("\n선택> ").strip().lower()

            if command == "help":
                self._print_help()

            elif command == "sync":
                self._handle_sync_corporations()
            
            elif command == "find":
                self._handle_find_corporation()
            
            elif command == "fs":
                self._handle_sync_financial_statements()

            elif command in {
                "exit",
                "quit",
            }:
                print("프로그램을 종료합니다.")
                break

            elif not command:
                continue

            else:
                print(
                    "알 수 없는 명령어입니다. "
                    "help를 입력하여 명령어를 확인하세요."
                )

    def _print_help(self) -> None:
        """
        사용 가능한 콘솔 명령어를 출력한다.
        """
        print(
            """
사용 가능한 명령어
------------------------------------------------------------
help                  명령어 목록 출력
sync                  DART 기업 고유번호 목록 동기화
find                  기업명 또는 종목코드로 기업 검색
fs                    기업 재무제표 수집 및 저장
exit                  프로그램 종료
"""
        )

    def _handle_sync_corporations(self) -> None:
        """
        DART 기업 고유번호 목록을 동기화한다.
        """
        print("\nDART 기업 고유번호 동기화를 시작합니다.")

        try:
            result = sync_corporations()

        except CorporationSyncError as error:
            print(f"동기화 실패: {error}")
            return

        except Exception as error:
            print(
                "동기화 중 예상하지 못한 오류가 "
                f"발생했습니다: {error}"
            )
            return

        print("\n동기화 완료")
        print(
            f"수신 기업 수: "
            f"{result['received_count']:,}"
        )
        print(
            f"저장 또는 갱신: "
            f"{result['saved_count']:,}"
        )
        print(
            f"종목코드 보유 기업: "
            f"{result['listed_count']:,}"
        )
        print(
            f"종목코드 미보유 기업: "
            f"{result['unlisted_count']:,}"
        )
        print(
            f"비활성화된 기업: "
            f"{result['deactivated_count']:,}"
        )
        print(
            f"동기화 시각: "
            f"{result['synced_at']}"
        )
    def _initialize_corporations(self) -> None:
        """
        기업 정보가 저장되어 있지 않은 경우에만
        최초 동기화를 수행한다.
        """
        corporation_count = count_corporations()

        if corporation_count > 0:
            print(
                f"\n저장된 기업 정보 "
                f"{corporation_count:,}개를 확인했습니다."
            )
            print(
                "기업목록 자동 동기화를 생략합니다."
            )
            return

        print("\n저장된 기업 정보가 없습니다.")
        print("최초 기업목록 동기화를 수행합니다.")

        self._handle_sync_corporations()
    def _handle_find_corporation(self) -> None:
        """
        기업명 또는 종목코드로 기업을 검색하고
        선택한 기업의 정보를 출력한다.
        """
        corporation = self._select_corporation()

        if corporation is None:
            return

        stock_code = corporation["stock_code"] or "비상장"

        print("\n[선택한 기업]")
        print("-" * 60)
        print(f"기업명: {corporation['corp_name']}")
        print(f"고유번호: {corporation['corp_code']}")
        print(f"종목코드: {stock_code}")
        print(
            f"최근 수정일: "
            f"{corporation['modify_date'] or '정보 없음'}"
        )
    def _select_corporation(self) -> dict | None:
        """
        기업명, 종목코드 또는 기업 고유번호를 입력받아
        검색 결과 중 하나를 선택하도록 한다.

        선택된 기업 정보를 반환하며,
        검색 또는 선택에 실패하면 None을 반환한다.
        """
        keyword = input(
            "기업명, 종목코드 또는 고유번호를 입력하세요: "
        ).strip()

        if not keyword:
            print("검색어를 입력해야 합니다.")
            return None

        try:
            result = find_corporations_with_count(
                keyword=keyword,
                limit=20,
                )

        except Exception as error:
            print(
                "기업 검색 중 오류가 발생했습니다: "
                f"{error}"
            )
            return None
        corporations = result["corporations"]
        total_count = result["total_count"]

        if not corporations:
            print("검색 결과가 없습니다.")
            return None

        print("\n[기업 검색 결과]")
        print("-" * 80)

        for index, corporation in enumerate(
            corporations,
            start=1,
        ):
            stock_code = (
                corporation["stock_code"]
                or "비상장"
            )

            print(
                f"{index}. "
                f"{corporation['corp_name']} "
                f"/ 종목코드: {stock_code} "
                f"/ 고유번호: {corporation['corp_code']}"
            )
        if total_count > len(corporations):
            print(
                f"\n검색 결과 {total_count:,}건 중 "
                f"{len(corporations):,}건만 표시했습니다."
            )
            print("더 구체적인 검색어를 입력해 주세요.")


        if len(corporations) == 1:
            print("\n검색 결과가 1개이므로 자동 선택합니다.")
            return corporations[0]

        selection = input(
            "\n선택할 기업 번호를 입력하세요: "
        ).strip()

        try:
            selected_index = int(selection) - 1

        except ValueError:
            print("숫자로 입력해야 합니다.")
            return None

        if not 0 <= selected_index < len(corporations):
            print("목록에 있는 번호를 입력하세요.")
            return None

        return corporations[selected_index]
    
    def _input_financial_statement_conditions(
        self,
    ) -> dict[str, str]:
        """
        재무제표 수집과 조회에 필요한 조건을 입력받는다.
        """
        bsns_year = self._input_business_year()
        reprt_code = self._input_report_code()
        fs_div = self._input_financial_statement_division()

        return {
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        }
    
    def _handle_sync_financial_statements(self) -> None:
        """
        기업과 보고서 조건을 입력받아
        DART 재무제표를 수집하고 DB에 저장한다.
        """
        corporation = self._select_corporation()

        if corporation is None:
            return

        conditions = (
            self._input_financial_statement_conditions()
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
    
    def _input_business_year(self) -> str:
        """
        사업연도를 입력받고 4자리 연도인지 검증한다.
        """
        while True:
            bsns_year = (
                input("사업연도 [기본값: 2025]: ")
                .strip()
                or "2025"
            )

            if not bsns_year.isdigit():
                print("사업연도는 숫자로 입력해야 합니다.")
                continue

            if len(bsns_year) != 4:
                print("사업연도는 4자리로 입력해야 합니다.")
                continue

            year = int(bsns_year)

            if year < 2000 or year > 2100:
                print("사업연도는 2000년부터 2100년 사이로 입력하세요.")
                continue

            return bsns_year
        
    def _input_report_code(self) -> str:
        """
        보고서 코드 또는 별칭을 입력받아 DART 보고서 코드로 반환한다.
        """
        print("\n입력 가능한 보고서 코드")
        print("--------------------------------")
        print("11011 / annual / a / 사업보고서 : 사업보고서")
        print("11013 / q1 / 1q / 1분기         : 1분기보고서")
        print("11012 / half / h / 반기          : 반기보고서")
        print("11014 / q3 / 3q / 3분기          : 3분기보고서")

        while True:
            value = (
                input("보고서 코드 [기본값: 11011]: ")
                .strip()
                or "11011"
            )

            normalized_value = value.lower()

            if value in REPORT_CODE_NAMES:
                return value

            if normalized_value in REPORT_CODE_ALIASES:
                return REPORT_CODE_ALIASES[normalized_value]

            print(
                "지원하지 않는 보고서 코드입니다. "
                "위 목록의 코드 또는 별칭을 입력하세요."
            )
    
    def _input_financial_statement_division(self) -> str:
        """
        연결 또는 별도 재무제표 구분을 입력받는다.
        """
        print("\n재무제표 구분")
        print("--------------------------------")
        print("CFS / 연결 / 연결재무제표 : 연결재무제표")
        print("OFS / 별도 / 개별         : 별도재무제표")

        while True:
            value = (
                input("재무제표 구분 [기본값: CFS]: ")
                .strip()
                or "CFS"
            )

            normalized_value = value.lower()

            if normalized_value in FS_DIV_ALIASES:
                return FS_DIV_ALIASES[normalized_value]

            print(
                "지원하지 않는 재무제표 구분입니다. "
                "CFS 또는 OFS를 입력하세요."
            )