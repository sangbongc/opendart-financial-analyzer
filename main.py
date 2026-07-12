from dart.client import DartClient


client = DartClient()

result = client.get(
    "/company.json",
    {
        "corp_code": "00126380",
    },
)

print(result)