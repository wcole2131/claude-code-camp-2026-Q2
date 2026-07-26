import io
import json
import urllib.error
from email.message import Message
from unittest.mock import MagicMock, patch

import pytest

from boukensha.client import Client
from boukensha.errors import ApiError


def make_builder(*, payload=None):
    builder = MagicMock()
    builder.url = "https://api.example.com/v1/messages"
    builder.headers = {"content-type": "application/json"}
    builder.to_api_payload.return_value = payload or {"model": "test-model"}
    return builder


def make_response(*, status=200, body=b'{"ok": true}'):
    response = MagicMock()
    response.status = status
    response.read.return_value = body
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def make_http_error(*, code, body=b"server error"):
    return urllib.error.HTTPError(
        url="https://api.example.com/v1/messages",
        code=code,
        msg="error",
        hdrs=Message(),
        fp=io.BytesIO(body),
    )


@patch("boukensha.client.time.sleep")
@patch("boukensha.client.urllib.request.urlopen")
def test_call_returns_parsed_json_on_success(mock_urlopen, mock_sleep):
    mock_urlopen.return_value = make_response(body=b'{"result": "ok"}')
    client = Client(make_builder())

    result = client.call()

    assert result == {"result": "ok"}
    assert mock_urlopen.call_count == 1
    mock_sleep.assert_not_called()


@patch("boukensha.client.time.sleep")
@patch("boukensha.client.urllib.request.urlopen")
def test_call_sends_the_builder_payload_as_the_request_body(mock_urlopen, mock_sleep):
    mock_urlopen.return_value = make_response()
    builder = make_builder(payload={"model": "claude-haiku-4-5", "max_tokens": 1024})
    client = Client(builder)

    client.call(max_output_tokens=2048)

    builder.to_api_payload.assert_called_once_with(max_output_tokens=2048)
    sent_request = mock_urlopen.call_args[0][0]
    assert json.loads(sent_request.data) == {"model": "claude-haiku-4-5", "max_tokens": 1024}
    assert sent_request.get_method() == "POST"


@patch("boukensha.client.time.sleep")
@patch("boukensha.client.urllib.request.urlopen")
def test_retries_on_retryable_status_code_then_succeeds(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [
        make_http_error(code=503),
        make_response(body=b'{"result": "ok"}'),
    ]
    client = Client(make_builder())

    result = client.call()

    assert result == {"result": "ok"}
    assert mock_urlopen.call_count == 2
    mock_sleep.assert_called_once_with(0.5)


@patch("boukensha.client.time.sleep")
@patch("boukensha.client.urllib.request.urlopen")
def test_retries_on_transient_exception_then_succeeds(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [
        ConnectionResetError("connection reset"),
        make_response(body=b'{"result": "ok"}'),
    ]
    client = Client(make_builder())

    result = client.call()

    assert result == {"result": "ok"}
    assert mock_urlopen.call_count == 2
    mock_sleep.assert_called_once_with(0.5)


@patch("boukensha.client.time.sleep")
@patch("boukensha.client.urllib.request.urlopen")
def test_raises_api_error_after_exhausting_retries_on_status_code(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [make_http_error(code=500, body=b"boom") for _ in range(4)]
    client = Client(make_builder())

    with pytest.raises(ApiError, match=r"failed after 4 attempts \(500\): boom"):
        client.call()

    assert mock_urlopen.call_count == 4
    assert mock_sleep.call_count == 3


@patch("boukensha.client.time.sleep")
@patch("boukensha.client.urllib.request.urlopen")
def test_raises_api_error_after_exhausting_retries_on_transient_exception(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [TimeoutError("timed out")] * 4
    client = Client(make_builder())

    with pytest.raises(ApiError, match=r"failed after 4 attempts: TimeoutError"):
        client.call()

    assert mock_urlopen.call_count == 4
    assert mock_sleep.call_count == 3


@patch("boukensha.client.time.sleep")
@patch("boukensha.client.urllib.request.urlopen")
def test_non_retryable_status_code_raises_immediately(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [make_http_error(code=401, body=b"unauthorized")]
    client = Client(make_builder())

    with pytest.raises(ApiError, match=r"failed after 1 attempt \(401\): unauthorized"):
        client.call()

    assert mock_urlopen.call_count == 1
    mock_sleep.assert_not_called()


@patch("boukensha.client.time.sleep")
@patch("boukensha.client.urllib.request.urlopen")
def test_retry_backoff_is_exponential(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [make_http_error(code=500) for _ in range(4)]
    client = Client(make_builder())

    with pytest.raises(ApiError):
        client.call()

    assert [call.args[0] for call in mock_sleep.call_args_list] == [0.5, 1.0, 2.0]
