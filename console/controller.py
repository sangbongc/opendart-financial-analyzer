from dart.corporation_service import (
    CorporationSyncError,
    sync_corporations,
)
from database.corporation_repository import (
    count_corporations,
)

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

            elif command == "sync-corporations":
                self._handle_sync_corporations()

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
sync-corporations     DART 기업 고유번호 목록 동기화
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