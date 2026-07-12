from config import DB_PATH
from database import create_tables


def main() -> None:
    create_tables()

    print("OpenDART 데이터베이스 초기화 완료")
    print(f"DB 경로: {DB_PATH}")


if __name__ == "__main__":
    main()