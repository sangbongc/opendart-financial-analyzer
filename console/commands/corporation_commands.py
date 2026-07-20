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