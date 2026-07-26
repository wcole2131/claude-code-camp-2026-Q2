# 04 · The API Client (Python port)

Python port of `week1_baseline/ruby/04_api_client`. Behavior matches the
Ruby implementation described in `../../ruby/04_api_client/README.md`; this
file documents the same design in Python terms.

`Client` takes the payload assembled by `PromptBuilder` and sends it to the
API. One HTTP POST, one response. No tool loop yet — just proving the round
trip works.

## New Files

| File | Description |
|---|---|
| `boukensha/client.py` | Makes the HTTP request and parses the response |

## Updated Files

| File | Change |
|---|---|
| `boukensha/errors.py` | Added `ApiError` for failed HTTP requests |
| `boukensha/tasks/base.py` | `provider`/`model`/`prompt_override` now tolerate non-dict `settings`, and the "required in settings.yaml" error messages fix a `.yml` typo |

## How It Works

```
PromptBuilder
      ↓
Client
      ↓
POST to API endpoint
      ↓
Raw JSON response
```

## `boukensha.Client`

| Method | Description |
|---|---|
| `call(max_output_tokens=1024)` | POSTs the payload and returns the parsed JSON response |

## Task Configuration

This step uses the same task-based configuration introduced in the earlier
baseline steps:

```yaml
tasks:
  player:
    provider: anthropic
    model: claude-haiku-4-5
    prompt_override:
      system: true
```

When `prompt_override.system` is true, Boukensha reads
`.boukensha/prompts/player/system.md`. Otherwise it falls back to this
step's shipped `prompts/system.md`.

Each backend validates the configured model at construction time.
Unsupported model names raise `UnsupportedModelError`, and supported models
expose backend-owned metadata such as `context_window`, `usage_unit`, and
token cost estimates for later logging steps.

## Retries

`Client.call` retries up to 3 times (4 attempts total) with exponential
backoff (`0.5s, 1s, 2s`) before raising `ApiError`, in two situations:

- **Retryable HTTP status codes**: `408, 409, 429, 500, 502, 503, 504`
- **Transient network errors**: connection reset/refused, timeouts, TLS
  errors, DNS failures, and the broader `urllib.error.URLError` `urlopen`
  wraps most connection-level failures in

Any other non-2xx response, or exhausting the retries, raises `ApiError`
with the attempt count and (for HTTP failures) the response status and body.

## No Dependencies

`Client` uses Python's standard `urllib.request` module. No third-party
packages, no new entry in `pyproject.toml`'s `dependencies`. This mirrors
the Ruby step's own design goal — the HTTP call itself is trivial and
should be visible in the code, not hidden behind a library.

## What the Response Looks Like

The raw response shape differs between backends. This is what you get back
from `client.call()` before any processing:

### Anthropic
```json
{
  "id": "msg_01XY",
  "type": "message",
  "role": "assistant",
  "content": [
    { "type": "text", "text": "Sure, let me read that file." }
  ],
  "stop_reason": "end_turn",
  "usage": { "input_tokens": 42, "output_tokens": 18 }
}
```

### Ollama
```json
{
  "model": "llama3.2",
  "message": {
    "role": "assistant",
    "content": "Sure, let me read that file."
  },
  "done_reason": "stop",
  "done": true
}
```

When the model wants to call a tool the response looks different. Anthropic
uses `stop_reason: "tool_use"` and adds a `tool_use` block to `content`.
Ollama adds a `tool_calls` array to `message`. Handling those differences is
the job of a later step — the Agent Loop.

## Considerations

**The client raises `ApiError` on failure.** A non-2xx response, or
exhausted retries, means something went wrong — bad API key, malformed
payload, server error. BOUKENSHA surfaces this explicitly rather than
returning a confusing `None` or partial response.

**TLS is handled automatically.** `urllib.request` picks HTTP vs. HTTPS
from the URL scheme and, for HTTPS, verifies against the system's default
CA store via `ssl.create_default_context()` — no manual certificate
wiring needed, matching the Ruby client's decision to omit an explicit
`ca_file` and let the platform supply its own trusted certs.

## A note on this step's live API call

Unlike every prior step, this example actually sends a request to a real
provider (Anthropic by default, per `.boukensha/settings.yaml`) and will
make a real, possibly-billed API call if you run it with a valid
`ANTHROPIC_API_KEY` (or whichever provider's key `tasks.player.provider`
selects) in `.boukensha/.env`. The exact JSON you get back depends on the
live model's response, so this README doesn't pin an "Expected Output"
block the way earlier steps do — the shape to expect is documented above
under "What the Response Looks Like".

`Client`'s retry/backoff/error-classification logic is covered by
`tests/test_client.py` against a mocked HTTP layer, so you don't need a
real API key to verify that logic is correct.

## Run Example

```bash
./week1_baseline/bin/python/04_api_client
```

Or directly:

```bash
cd week1_baseline/python/04_api_client
uv run python examples/example.py
```

Requires a real API key for the configured provider in `.boukensha/.env`.

## Tests

```bash
cd week1_baseline/python/04_api_client
make test    # uv run pytest -v
make lint    # uv run isort --check-only / ruff check / ty check
```
