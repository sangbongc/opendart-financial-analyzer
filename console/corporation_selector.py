from dart.corporation_service import find_corporations_with_count


def select_corporation() -> dict | None:
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