from dart.corporation_service import (
    CorporationSyncError,
    sync_corporations,
)
from database.schema import create_tables


def main() -> None:
    print("DART 기업 고유번호 동기화를 시작합니다.")

    create_tables()

    try:
        result = sync_corporations()

    except CorporationSyncError as error:
        print(f"동기화 실패: {error}")
        return

    except Exception as error:
        print(f"예상하지 못한 오류가 발생했습니다: {error}")
        return

    print("\n동기화 완료")
    print(f"수신 기업 수: {result['received_count']:,}")
    print(f"저장 또는 갱신: {result['saved_count']:,}")
    print(f"종목코드 보유 기업: {result['listed_count']:,}")
    print(f"종목코드 미보유 기업: {result['unlisted_count']:,}")
    print(f"비활성화된 기업: {result['deactivated_count']:,}")
    print(f"동기화 시각: {result['synced_at']}")


if __name__ == "__main__":
    main()