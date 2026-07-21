from io import BytesIO
from unittest.mock import Mock, patch
from zipfile import ZipFile

import pytest

from dart.xbrl_file_service import (
    XbrlArchiveError,
    XbrlFileDownloadError,
    download_and_inspect_xbrl,
    download_xbrl_archive,
    get_xbrl_archive_file_names,
)


def make_zip_content(
    files: dict[str, str],
) -> bytes:
    """
    테스트용 ZIP 바이너리를 생성한다.
    """
    buffer = BytesIO()

    with ZipFile(buffer, "w") as archive:
        for file_name, file_content in files.items():
            archive.writestr(
                file_name,
                file_content,
            )

    return buffer.getvalue()


@patch("dart.xbrl_file_service.DartClient")
def test_download_xbrl_archive(
    mock_client_class: Mock,
):
    client = Mock()
    mock_client_class.return_value = client

    zip_content = make_zip_content(
        {
            "financial_statement.xml": "<xml />",
        }
    )

    client.download.return_value = zip_content

    result = download_xbrl_archive(
        rcept_no="20260317001234",
        reprt_code="11011",
    )

    assert result == zip_content

    client.download.assert_called_once_with(
        "/fnlttXbrl.xml",
        {
            "rcept_no": "20260317001234",
            "reprt_code": "11011",
        },
    )


@pytest.mark.parametrize(
    "rcept_no, reprt_code, expected_message",
    [
        (
            "",
            "11011",
            "접수번호를 입력해야 합니다.",
        ),
        (
            "   ",
            "11011",
            "접수번호를 입력해야 합니다.",
        ),
        (
            "20260317001234",
            "",
            "보고서 코드를 입력해야 합니다.",
        ),
        (
            "20260317001234",
            "   ",
            "보고서 코드를 입력해야 합니다.",
        ),
    ],
)
def test_download_xbrl_archive_validates_input(
    rcept_no: str,
    reprt_code: str,
    expected_message: str,
):
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        download_xbrl_archive(
            rcept_no=rcept_no,
            reprt_code=reprt_code,
        )


@patch("dart.xbrl_file_service.DartClient")
def test_download_xbrl_archive_wraps_client_error(
    mock_client_class: Mock,
):
    client = Mock()
    mock_client_class.return_value = client

    client.download.side_effect = RuntimeError(
        "HTTP 오류"
    )

    with pytest.raises(
        XbrlFileDownloadError,
        match="XBRL 파일 다운로드에 실패했습니다",
    ):
        download_xbrl_archive(
            rcept_no="20260317001234",
            reprt_code="11011",
        )


@patch("dart.xbrl_file_service.DartClient")
def test_download_xbrl_archive_rejects_empty_response(
    mock_client_class: Mock,
):
    client = Mock()
    mock_client_class.return_value = client

    client.download.return_value = b""

    with pytest.raises(
        XbrlFileDownloadError,
        match="응답이 비어 있습니다",
    ):
        download_xbrl_archive(
            rcept_no="20260317001234",
            reprt_code="11011",
        )


@patch("dart.xbrl_file_service.DartClient")
def test_download_xbrl_archive_rejects_non_zip_response(
    mock_client_class: Mock,
):
    client = Mock()
    mock_client_class.return_value = client

    client.download.return_value = (
        b'<?xml version="1.0"?>'
        b"<result>"
        b"<status>013</status>"
        b"</result>"
    )

    with pytest.raises(
        XbrlArchiveError,
        match="정상적인 XBRL ZIP 파일이 아닙니다",
    ):
        download_xbrl_archive(
            rcept_no="20260317001234",
            reprt_code="11011",
        )


def test_get_xbrl_archive_file_names():
    zip_content = make_zip_content(
        {
            "instance.xml": "<xml />",
            "taxonomy/schema.xsd": "<schema />",
            "taxonomy/label.xml": "<label />",
        }
    )

    result = get_xbrl_archive_file_names(
        zip_content
    )

    assert result == [
        "instance.xml",
        "taxonomy/schema.xsd",
        "taxonomy/label.xml",
    ]


def test_get_xbrl_archive_file_names_rejects_invalid_zip():
    with pytest.raises(
        XbrlArchiveError,
        match="읽을 수 없습니다",
    ):
        get_xbrl_archive_file_names(
            b"not a zip file"
        )


@patch("dart.xbrl_file_service.download_xbrl_archive")
def test_download_and_inspect_xbrl(
    mock_download: Mock,
):
    zip_content = make_zip_content(
        {
            "instance.xml": "<xml />",
            "schema.xsd": "<schema />",
        }
    )

    mock_download.return_value = zip_content

    result = download_and_inspect_xbrl(
        rcept_no="20260317001234",
        reprt_code="11011",
    )

    assert result == [
        "instance.xml",
        "schema.xsd",
    ]

    mock_download.assert_called_once_with(
        rcept_no="20260317001234",
        reprt_code="11011",
    )