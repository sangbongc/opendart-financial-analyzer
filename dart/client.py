import requests

from config import BASE_URL, CRTFC_KEY, TIMEOUT


class DartAPIError(Exception):
    """OpenDART API가 오류 상태를 반환했을 때 발생하는 예외입니다."""

    def __init__(self, status: str, message: str):
        self.status = status
        self.message = message

        super().__init__(
            f"OpenDART API 오류 [{status}]: {message}"
        )


class DartClient:
    """OpenDART API 공통 HTTP 클라이언트입니다."""

    def get(
        self,
        endpoint: str,
        params: dict | None = None,
    ) -> dict:
        request_params = dict(params or {})
        request_params["crtfc_key"] = CRTFC_KEY

        response = requests.get(
            BASE_URL + endpoint,
            params=request_params,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        status = data.get("status")
        message = data.get("message", "알 수 없는 오류")

        if status != "000":
            raise DartAPIError(
                status=status or "UNKNOWN",
                message=message,
            )

        return data

    def get_binary(
        self,
        endpoint: str,
        params: dict | None = None,
    ) -> bytes:
        """
        ZIP 파일처럼 JSON이 아닌 바이너리 응답을 내려받는다.
        """
        request_params = dict(params or {})
        request_params["crtfc_key"] = CRTFC_KEY

        response = requests.get(
            BASE_URL + endpoint,
            params=request_params,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        if not response.content:
            raise DartAPIError(
                status="EMPTY_RESPONSE",
                message="OpenDART 응답 내용이 비어 있습니다.",
            )

        return response.content