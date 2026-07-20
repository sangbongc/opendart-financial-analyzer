from dart.corporation_service import (
    CorporationSyncError,
    sync_corporations,
    find_corporations,
    find_corporations_with_count
)
from database.corporation_repository import (
    count_corporations,
)
from console.corporation_selector import(
    select_corporation
)
from utils import (
    REPORT_CODE_ALIASES,
    REPORT_CODE_NAMES,
    FS_DIV_ALIASES,
)


def initialize_corporations() -> None:
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

        handle_sync_corporations()


def handle_sync_corporations() -> None:
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


def handle_find_corporation() -> None:
        """
        기업명 또는 종목코드로 기업을 검색하고
        선택한 기업의 정보를 출력한다.
        """
        corporation = select_corporation()

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


def input_financial_statement_conditions() -> dict[str, str]:
        """
        재무제표 수집과 조회에 필요한 조건을 입력받는다.
        """
        bsns_year = input_business_year()
        reprt_code = input_report_code()
        fs_div = input_financial_statement_division()

        return {
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        }


def input_business_year() -> str:
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
        

def input_report_code() -> str:
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
    

def input_financial_statement_division() -> str:
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
