# Python Port Plan · 04 · The API Client

Status: DONE — open questions answered (recommendations accepted) and implementation applied.
`uv run pytest -v` (81 passed), `isort --check-only`, `ruff check`, and `ty check` all pass in
`week1_baseline/python/04_api_client/`. The example script was **not** run live — running it as
shipped makes a real network call to `api.anthropic.com` even with an empty API key present (see
open question 2), so live-launcher verification is deferred until the user supplies a real key and
asks for it explicitly.

## Goal

Turn `week1_baseline/python/04_api_client/` (currently an exact clone of
`python/03_prompt_builder`, still describing "Step 3: Prompt Builder" throughout) into a correct
port of `@week1_baseline/ruby/04_api_client/`, by applying only the delta Ruby itself made going
from `03_prompt_builder` to `04_api_client` — same copy-prior-step-then-apply-delta workflow used
for every step so far.

This step adds a `Client` that actually sends the `PromptBuilder`-assembled payload over HTTP and
parses the response — the first step in the port that performs a real network call to a paid
third-party API (Anthropic, OpenAI, Gemini, etc.), rather than only building an in-memory payload.
That changes what "verify by running it" safely means here — see the Verification section below.

## How this plan was created

1. Confirmed `week1_baseline/python/04_api_client/` is byte-identical to
   `week1_baseline/python/03_prompt_builder/` (`diff -rq`, excluding
   `.venv`/`__pycache__`/`.ruff_cache`/`.pytest_cache`/`uv.lock`) — the copy-forward step is
   already done, only the delta needs applying.
2. Diffed every non-vendored file between `@week1_baseline/ruby/03_prompt_builder/` and
   `@week1_baseline/ruby/04_api_client/` (`diff -rq`, excluding `vendor/`, `.bundle/`,
   `Gemfile.lock`, `.gitignore`) to get the exact delta: `README.md`, `examples/example.rb`,
   `lib/boukensha/config.rb`, `lib/boukensha/errors.rb`, `lib/boukensha/tasks/base.rb`,
   `lib/boukensha.rb`, `prompts/system.md` changed; `lib/boukensha/client.rb` is new;
   `Gemfile`, `lib/boukensha/registry.rb`, `lib/boukensha/tool.rb`, `lib/boukensha/message.rb`,
   `lib/boukensha/context.rb`, `lib/boukensha/prompt_builder.rb`, `lib/boukensha/tasks/player.rb`,
   and every file under `lib/boukensha/backends/` are byte-identical, unchanged.
3. Read every changed/new Ruby file in full: `README.md`, `lib/boukensha/client.rb`,
   `lib/boukensha.rb`, `lib/boukensha/config.rb`, `lib/boukensha/errors.rb`,
   `lib/boukensha/tasks/base.rb`, `examples/example.rb`, `prompts/system.md`. Ran precise
   `diff -u` on each changed file rather than relying on prose summaries.
4. Confirmed `.boukensha/settings.yaml` at the repo root has `tasks.player.prompt_override.system:
   true` and `.boukensha/prompts/player/system.md` exists — relevant to a `PROMPTS_DIR` question
   below.
5. Confirmed `.boukensha/.env` at the repo root has `ANTHROPIC_API_KEY=` (present but **empty**,
   likewise for `OPENAI_API_KEY`/`GEMINI_API_KEY`/`OLLAMA_API_KEY`) — no real credentials are
   configured on this machine.
6. Read the current Python scaffold in full to confirm what's reusable as-is and to pull exact
   conventions already established: `boukensha/config.py`, `boukensha/errors.py`,
   `boukensha/tasks/base.py`, `boukensha/__init__.py`, `boukensha/prompt_builder.py`,
   `boukensha/backends/base.py` (confirms every backend already exposes `.headers` and `.url`
   properties, which `Client` needs), `examples/example.py`, and existing test file naming in
   `tests/` (`test_backends.py`, `test_prompt_builder.py`, etc.) to match for a new `test_client.py`.
7. Confirmed `week1_baseline/bin/python/04_api_client` does not exist yet (only `bin/python/00`
   through `03` do), same gap pattern filled in every previous port.
8. Ran `python -c` to confirm the Ruby-04 `PROMPTS_DIR` constant, as literally written, resolves
   to a directory that doesn't exist (`week1_baseline/ruby/prompts` — one `../` too many); see the
   "Discovered issue" note below.

## Starting point (what's already in place, unchanged)

`week1_baseline/python/04_api_client/` is currently byte-identical to
`week1_baseline/python/03_prompt_builder/`. These files need **no changes** because their Ruby
originals are identical between the two steps:

- `boukensha/context.py`, `boukensha/tool.py`, `boukensha/message.py`, `boukensha/registry.py`
- `boukensha/prompt_builder.py`
- `boukensha/backends/base.py`, `.../anthropic.py`, `.../gemini.py`, `.../ollama.py`,
  `.../ollama_cloud.py`, `.../openai.py`
- `boukensha/tasks/player.py`, `boukensha/tasks/__init__.py`
- `tests/test_config.py`, `tests/test_context.py`, `tests/test_message.py`,
  `tests/test_registry.py`, `tests/test_tool.py`, `tests/test_backends.py`,
  `tests/test_prompt_builder.py`, `tests/test_tasks.py`
- `.gitignore`, `Makefile`, `.python-version`

## The exact delta (from `diff -u` between the two Ruby steps)

`@week1_baseline/ruby/03_prompt_builder/lib/boukensha.rb` →
`@week1_baseline/ruby/04_api_client/lib/boukensha.rb`: adds `require_relative "boukensha/client"`;
also **drops** the standalone `require_relative "boukensha/backends/base"` line. That drop is not
a behavior change — every backend file (`anthropic.rb`, `gemini.rb`, etc.) already does its own
`require_relative "base"` before defining itself, so `backends/base` was always getting loaded
twice; Ruby's `require_relative` is idempotent, so removing the redundant top-level require is a
no-op cleanup, nothing to port.

New file `@week1_baseline/ruby/04_api_client/lib/boukensha/client.rb`: `Boukensha::Client` —
`initialize(builder)` stores `@builder`; `call(max_output_tokens: 1024)` builds a
`Net::HTTP::Post` from `builder.url`/`builder.headers`/`builder.to_api_payload(...)`, retries on
a fixed set of retryable HTTP status codes (`408, 409, 429, 500, 502, 503, 504`) and a fixed set
of transient network exceptions (connection reset/refused, timeouts, SSL errors, socket errors,
`EOFError`), up to `MAX_RETRIES = 3` with exponential backoff (`0.5 * 2**(attempt-1)` seconds),
raises `ApiError` if retries are exhausted or the final response isn't 2xx, and otherwise returns
`JSON.parse(response.body)`.

`@week1_baseline/ruby/03_prompt_builder/lib/boukensha/errors.rb` →
`.../04_api_client/lib/boukensha/errors.rb`: adds `class ApiError < StandardError; end`.

`@week1_baseline/ruby/03_prompt_builder/lib/boukensha/config.rb` →
`.../04_api_client/lib/boukensha/config.rb`: two changes, both cosmetic/non-behavioral for the
Python port —
(a) the `PROMPTS_DIR` comment changes from "shipped alongside the gem/library code" to "shipped
alongside this step" (no path or behavior change, pure comment wording); note the path *literal*
also changed (`"../../prompts"` → `"../../../prompts"`), but that's a Ruby-directory-nesting
artifact only — see "Discovered issue" below, it does not need to be mirrored in Python;
(b) a trailing blank line before `end`/`end` — no-op.

`@week1_baseline/ruby/03_prompt_builder/lib/boukensha/tasks/base.rb` →
`.../04_api_client/lib/boukensha/tasks/base.rb`: two changes —
(a) fixes a typo in two `ArgumentError` messages: `"...required in settings.yml"` →
`"...required in settings.yaml"` (both the `provider` and `model` error messages);
(b) the private `fetch(settings, key)` helper gains a guard: `return nil unless
settings.is_a?(Hash)` before indexing — makes `provider`/`model`/`prompt_override?` (all of which
call `fetch`) safely return `nil`/`false` instead of raising `NoMethodError` if `settings` is ever
something other than a Hash (e.g. `nil`, or a malformed YAML value).

`@week1_baseline/ruby/03_prompt_builder/prompts/system.md` → `.../04_api_client/prompts/system.md`:
default system prompt text rewritten from a MUD-flavored assistant description to a more general
"You are Boukensha, an autonomous player exploring a CircleMUD world..." framing. Copy verbatim —
this file is only reached as a fallback when `prompt_override.system` is false or the user prompt
file is missing, which isn't the case in this repo's own `.boukensha/settings.yaml` (see below),
but it must still match for anyone running without a `prompt_override`.

`@week1_baseline/ruby/03_prompt_builder/examples/example.rb` →
`.../04_api_client/examples/example.rb`: rewritten. Swaps the `look`/`move` demo tools for
`read_file`/`list_directory` (both operating on the real filesystem — `File.read(path)` and
`Dir.entries(path).reject { |f| f.start_with?(".") }.join("\n")`); drops the three manually-seeded
`ctx.add_message` calls except one (`"What files are in the current directory?"`, as `:user`);
builds `client = Boukensha::Client.new(builder)` and actually calls `client.call`, printing
`"Sending request to #{builder.url}..."` then the pretty-printed raw JSON response instead of the
in-memory payload dump the `03_prompt_builder` example printed. Banner text becomes `"=== BOUKENSHA
Step 4: API Client ==="`.

`Gemfile`, `lib/boukensha/registry.rb`, `lib/boukensha/tool.rb`, `lib/boukensha/message.rb`,
`lib/boukensha/context.rb`, `lib/boukensha/prompt_builder.rb`, `lib/boukensha/tasks/player.rb`,
every file under `lib/boukensha/backends/`: unchanged, byte-identical between the two Ruby steps.

### Discovered issue: Ruby's `PROMPTS_DIR` in this step resolves to a nonexistent directory

`Config::PROMPTS_DIR = File.expand_path("../../../prompts", __dir__)` in
`04_api_client/lib/boukensha/config.rb` — resolved from `lib/boukensha/`, three levels up lands at
`week1_baseline/ruby/prompts` (one level *above* the `04_api_client/` directory), which does not
exist (confirmed: `ls week1_baseline/ruby/prompts` → no such directory). This looks like an
off-by-one introduced in this step's Ruby source (it should be `"../../prompts"`, two levels up,
matching every prior step and landing correctly on `04_api_client/prompts`). It doesn't visibly
break the shipped example because `.boukensha/settings.yaml` sets `prompt_override.system: true`
and `.boukensha/prompts/player/system.md` exists, so `PROMPTS_DIR` is never actually consulted —
but running the Ruby example with `prompt_override.system: false` (or no override configured)
would silently return `nil` for the default system prompt.

The current Python `Config.PROMPTS_DIR` (`Path(__file__).resolve().parent.parent / "prompts"`,
already in place from `03_prompt_builder`) is **already correct** — it's anchored two levels up
from `boukensha/config.py` (one level shallower than Ruby's `lib/boukensha/config.rb`, since the
Python package has no `lib/` wrapper), which lands on `04_api_client/prompts` exactly as intended.
**Recommendation: do not port the Ruby off-by-one.** Leave `PROMPTS_DIR` as the existing, already-
correct Python expression; only update the docstring/comment wording to match ("shipped alongside
this step") if you want comment-level fidelity. This is called out explicitly rather than silently
fixed-and-unmentioned, per this project's practice of noting discrepancies instead of hiding them
(see `02_the_registry`'s note about a stale `budget=8192` README field).

## Delta to apply to `python/04_api_client`

| Change | File(s) | Action |
|---|---|---|
| Add `ApiError` | `boukensha/errors.py` | add `class ApiError(Exception): pass` |
| Add the HTTP client | `boukensha/client.py` (new) | port `Client` per the mapping table below — retry loop, status-code/exception classification, `ApiError` on failure, parsed-JSON return |
| Fix error message typo | `boukensha/tasks/base.py` | change both `"...required in settings.yml"` strings to `"...required in settings.yaml"`, matching Ruby's fix |
| Guard non-dict settings | `boukensha/tasks/base.py` | make `provider`/`model`/`prompt_override` tolerate non-dict `settings` the same way Ruby's `fetch` guard now does — see mapping table |
| Leave `PROMPTS_DIR` alone | `boukensha/config.py` | **no code change** — already correct; optionally update the adjacent comment text only (see "Discovered issue" above) |
| Export new symbol | `boukensha/__init__.py` | add `Client` to imports/`__all__` |
| Copy default prompt | `prompts/system.md` | replace with `@week1_baseline/ruby/04_api_client/prompts/system.md`'s text, verbatim |
| Rewrite the example | `examples/example.py` | replace the `03_prompt_builder`-style payload dump with the `read_file`/`list_directory` tools + real `Client.call()` demo, per `@week1_baseline/ruby/04_api_client/examples/example.rb` — see script below |
| Add the launcher | `week1_baseline/bin/python/04_api_client` (new) | mirror `@week1_baseline/bin/python/03_prompt_builder`'s shape |
| Rewrite docs | `README.md` | adapt from `@week1_baseline/ruby/04_api_client/README.md` — Client method table, no-dependencies note, considerations (`ApiError`, SSL handling), Python run instructions; skip porting the Ruby README's own typo'd "Output eaxmple" section verbatim, and see the Verification section below for what output to actually document |
| Update package metadata | `pyproject.toml` | `description` → `"— 04: api client"`; **no new runtime dependency** — Ruby's own README frames `net/http`-only, no-gems as an intentional design choice for this step, and the Python equivalent (`urllib.request`, stdlib) preserves that intentionally-visible, no-library principle |
| Nothing to do | see "Starting point" above | already correct, Ruby originals didn't change |

## Ruby → Python behavior mapping

| Ruby | Python equivalent | Notes |
|---|---|---|
| `require "net/http"` / `Net::HTTP.new(...).request(...)`, no gem | `urllib.request` (stdlib) | preserves the Ruby README's explicit "no dependencies, HTTP call should be visible not hidden behind a library" design goal — don't reach for `requests` here |
| `Net::HTTP::Post.new(uri, headers)` + `request.body = payload.to_json` | `urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")` | |
| `http.use_ssl = uri.scheme == "https"` (explicit toggle) | nothing explicit needed | `urllib.request.urlopen` picks HTTP vs HTTPS from the URL scheme automatically |
| `http.verify_mode = OpenSSL::SSL::VERIFY_PEER` + omitted `ca_file` (comment: let OpenSSL find system certs) | nothing explicit needed | `urllib.request`'s default HTTPS handler uses `ssl.create_default_context()`, which verifies against the system CA store the same way — no manual cert-file wiring required on either side |
| `response.is_a?(Net::HTTPSuccess)` (net/http returns a response object for *any* status) | `urllib.error.HTTPError` (raised, not returned, for any non-2xx status) | **key control-flow difference** — net/http hands back a response you inspect; `urlopen` raises on non-2xx. Catch `urllib.error.HTTPError` to get `.code` and `.read()` (the body) for retry-status-code checks and for building the `ApiError` message; catch `urllib.error.URLError` (its non-HTTP superclass/sibling) for connection-level failures |
| `TRANSIENT_ERRORS = [EOFError, Errno::ECONNRESET, Errno::ECONNREFUSED, Net::OpenTimeout, Net::ReadTimeout, OpenSSL::SSL::SSLError, SocketError, Timeout::Error]` | `(EOFError, ConnectionResetError, ConnectionRefusedError, TimeoutError, ssl.SSLError, socket.gaierror, urllib.error.URLError)` | `TimeoutError`/`socket.timeout` are the same object since Python 3.10; `socket.gaierror` covers DNS-resolution failures (Ruby's `SocketError`); `urllib.error.URLError` is the catch-all `urlopen` wraps most connection-level failures in, so it should be caught too even though it's not a 1:1 exception-for-exception match |
| `RETRYABLE_STATUS_CODES = [408, 409, 429, 500, 502, 503, 504]` | same literal list | no translation needed, just re-declare as a Python set/tuple |
| `MAX_RETRIES = 3`, `BASE_RETRY_DELAY = 0.5`, `retry_delay(attempt) = BASE_RETRY_DELAY * (2**(attempt-1))` | same constants/formula, `import time; time.sleep(...)` | |
| `raise ApiError, "..."` / `rescue *TRANSIENT_ERRORS => e` | `raise ApiError("...")` / `except (EOFError, ConnectionResetError, ...) as e:` | plain exception, same as `UnknownToolError`/`UnsupportedModelError` |
| `JSON.parse(response.body)` | `json.loads(response.read())` (inside the `urlopen` context) | |
| `fetch(settings, key)` gaining `return nil unless settings.is_a?(Hash)` | `if not isinstance(settings, dict): return None` guard at the top of `provider`/`model`/`prompt_override` (or a small shared `_fetch` helper mirroring Ruby's) before the existing `(settings or {}).get(...)` calls | Python's current `(settings or {}).get(...)` already tolerates `None`/`{}` but would raise `AttributeError` on a non-dict truthy value (e.g. a stray string in malformed YAML) the way Ruby's *old*, unguarded `fetch` would raise `NoMethodError` — this closes that gap to match Ruby's new guard |

## Decisions carried over (no longer open)

- **Copy-forward-then-delta workflow**, `uv` + `hatchling`, flat `boukensha/` layout,
  `.python-version` = 3.14, `ruff`/`isort`/`ty` via `uv run`, `pytest` in `tests/` — unchanged,
  applied again here.
- **`dict.get`-only lookups, no symbol/string duality** — settled in `00_config`; the new
  non-dict-settings guard above is an *additive* safety check, not a reintroduction of Ruby's
  symbol/string key duality.
- **Duck-typed `NotImplementedError` for class-level abstract methods** — settled in `00_config`;
  `Backends::Base.headers`/`.url` (already implemented this way) is what `Client` calls into,
  unaffected by this step.

## Open questions (please answer before implementation)

1. **stdlib HTTP mechanism** — `urllib.request` (higher-level, raises `HTTPError` on non-2xx,
   handles TLS via a default `ssl` context automatically) vs. `http.client` (lower-level, closer
   to a literal line-for-line mirror of `Net::HTTP`'s "build request, get response object back,
   inspect status yourself" shape, but noticeably more boilerplate — manual `putrequest`/
   `putheader`/`endheaders`/`getresponse`, and no automatic TLS context). *Recommendation:
   `urllib.request` — it's stdlib-only (preserving the Ruby README's "no dependencies" intent),
   handles HTTPS transparently, and Python code that retries by catching `HTTPError` is idiomatic,
   not a workaround.*
   Use the recommendation provided for this step.
2. **Live-API verification** — this is the first step whose example makes a real network call to
   a paid third-party API (Anthropic by default, per `.boukensha/settings.yaml`). This repo's
   `ANTHROPIC_API_KEY` (and the other provider keys) are present in `.boukensha/.env` but
   **currently empty** — running either launcher as-is will fail at `ENV.fetch("ANTHROPIC_API_KEY")`
   / `os.environ["ANTHROPIC_API_KEY"]` before any request is even sent. Options: (a) you supply a
   real key and explicitly ask for the launcher(s) to be run, understanding it will make a real,
   possibly-billed API call — I will not do this unprompted; (b) verify structurally instead —
   `pytest` coverage for `Client` that exercises the retry/status/exception logic against a mocked
   HTTP layer (e.g. `unittest.mock.patch("urllib.request.urlopen")`), without any real network
   call, and verify the example script only up to the point of printing `"Sending request to
   ..."` (confirming config/tool/message wiring matches Ruby) without actually invoking
   `client.call()`. *Recommendation: (b) by default — mocked tests are the real verification
   surface for this step's new logic (retry backoff, status-code classification, `ApiError`
   construction), which a single live call wouldn't exercise anyway (you'd only ever see the
   happy path or whatever error your key/network happens to produce that day). If you want a real
   end-to-end smoke test too, that's a separate, explicit, opt-in step — say so and supply a key.*
   - Use the recommendation provided for this step.
3. **Non-dict `settings` guard** — confirmed above as a straight port of Ruby's new `fetch` guard.
   Flagging only for explicit sign-off since it changes existing Python method behavior
   (previously would raise `AttributeError` on malformed non-dict settings; will now return
   `None`/`False`), even though it's a strict porting-fidelity improvement, not a new design
   choice.
   - Use the recommendation provided for this step.
4. **Retry/backoff test coverage shape** — given open question 2's recommendation, should
   `tests/test_client.py` fake `time.sleep` (e.g. patch it to a no-op) so retry-backoff tests run
   instantly, or actually sleep in tests (slower, but exercises the real `time.sleep` call path)?
   *Recommendation: patch `time.sleep` to a no-op in tests that exercise retries — keeps the test
   suite fast, and the backoff *formula* itself is easy to assert on directly without waiting for it.*
   - Use the recommendation provided for this step.

## Implementation steps (once questions above are answered)

1. Add `ApiError` to `boukensha/errors.py`.
2. Add `boukensha/client.py` with `Client` (retry loop, status/exception classification per the
   mapping table, `ApiError` on exhausted retries or a final non-2xx, `json.loads` on success).
3. Fix the `settings.yml` → `settings.yaml` typo and add the non-dict `settings` guard in
   `boukensha/tasks/base.py`.
4. Leave `boukensha/config.py`'s `PROMPTS_DIR` code as-is (already correct); optionally update its
   adjacent comment text only.
5. Update `boukensha/__init__.py` to export `Client`.
6. Replace `prompts/system.md` with the new Ruby step's text, verbatim.
7. Rewrite `examples/example.py`: swap `look`/`move` tools for `read_file`/`list_directory`,
   trim the seeded messages to the single `"What files are in the current directory?"` user
   message, construct `Client(builder)`, print the `"=== BOUKENSHA Step 4: API Client ==="` banner
   and `"Sending request to {builder.url}..."` line; only call `client.call()` and print the raw
   response if open question 2 is resolved in favor of a live call.
8. Add `week1_baseline/bin/python/04_api_client` launcher.
9. Rewrite `week1_baseline/python/04_api_client/README.md` adapted from
   `@week1_baseline/ruby/04_api_client/README.md`.
10. Update `pyproject.toml`'s `description` field to `"— 04: api client"`.
11. Add `tests/test_client.py`: mocked-`urlopen` coverage for a successful call (parses and
    returns JSON), a retryable-status-code response that eventually succeeds, a
    transient-exception response that eventually succeeds, and both "retries exhausted" cases
    (status-based and exception-based) raising `ApiError` with a message that includes the
    attempt count. Add/extend `tests/test_tasks.py` for the non-dict-`settings` guard and the
    corrected error-message text.
12. Verify per open question 2: run `uv run pytest -v && make lint` in
    `week1_baseline/python/04_api_client/`; only run the actual launchers
    (`week1_baseline/bin/python/04_api_client` / `week1_baseline/bin/ruby/04_api_client`) against
    a live API if the user has supplied a real key and explicitly asked for that comparison.
