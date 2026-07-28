from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any

from .errors import ApiError

if TYPE_CHECKING:
    from .prompt_builder import PromptBuilder

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
TRANSIENT_ERRORS = (
    EOFError,
    ConnectionResetError,
    ConnectionRefusedError,
    TimeoutError,
    ssl.SSLError,
    socket.gaierror,
    urllib.error.URLError,
)
MAX_RETRIES = 3
BASE_RETRY_DELAY = 0.5


class Client:
    def __init__(self, builder: PromptBuilder) -> None:
        self.builder = builder

    def call(self, *, max_output_tokens: int = 1024, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        payload = json.dumps(
            self.builder.to_api_payload(max_output_tokens=max_output_tokens, tools=tools)
        ).encode()
        request = urllib.request.Request(
            self.builder.url,
            data=payload,
            headers=self.builder.headers,
            method="POST",
        )

        attempts = 0
        status: int | None = None
        body = b""

        while True:
            attempts += 1

            try:
                with urllib.request.urlopen(request) as response:
                    status = response.status
                    body = response.read()
            except urllib.error.HTTPError as e:
                status = e.code
                body = e.read()
            except TRANSIENT_ERRORS as e:
                if attempts > MAX_RETRIES:
                    raise ApiError(f"API request failed after {attempts} attempts: {type(e).__name__}: {e}") from e
                time.sleep(self._retry_delay(attempts))
                continue

            if status in RETRYABLE_STATUS_CODES and attempts <= MAX_RETRIES:
                time.sleep(self._retry_delay(attempts))
                continue

            break

        if status == 401:
            raise ApiError("authentication failed (401) — check your API key")

        if status is None or not (200 <= status < 300):
            suffix = "" if attempts == 1 else "s"
            raise ApiError(f"API request failed after {attempts} attempt{suffix} ({status}): {body.decode(errors='replace')}")

        return json.loads(body)

    @staticmethod
    def _retry_delay(attempt: int) -> float:
        return BASE_RETRY_DELAY * (2 ** (attempt - 1))
