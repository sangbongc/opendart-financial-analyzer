from dart.client import DartAPIError, DartClient


client = DartClient()

try:
    result = client.get(
        "/company.json",
        {
            "corp_code": "00126380",
        },
    )

    print("회사명:", result["corp_name"])
    print("종목코드:", result["stock_code"])
    print("대표자:", result["ceo_nm"])

except DartAPIError as error:
    print(error)