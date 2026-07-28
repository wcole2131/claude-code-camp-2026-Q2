from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .errors import ApiError
from .logger import Logger

if TYPE_CHECKING:
    from .client import Client
    from .context import Context
    from .prompt_builder import PromptBuilder
    from .registry import Registry


class Agent:
    # Default iteration ceiling. The *enforced* value comes from the
    # max_iterations constructor arg (sourced from Config at the run/repl path),
    # which falls back to this constant. 0 (or None) disables the ceiling.
    MAX_ITERATIONS = 25

    # The wind-down call is deliberately short and cheap.
    WRAP_UP_OUTPUT_TOKENS = 400
    WRAP_UP_DIRECTIVE = (
        "You have reached your action limit for this turn. Do not call any more tools.\n"
        "Briefly summarize what you accomplished, what is still unfinished, and the\n"
        "single next action you would take."
    ).strip()

    def __init__(
        self,
        *,
        context: Context,
        registry: Registry,
        builder: PromptBuilder,
        client: Client,
        logger: Logger | None = None,
        task_settings: dict[str, Any] | None = None,
        max_iterations: int | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self.context = context
        self.registry = registry
        self.builder = builder
        self.client = client
        self.logger = logger if logger is not None else Logger()
        self._max_iterations = self._resolve_max_iterations(task_settings, max_iterations)
        self._max_output_tokens = self._resolve_max_output_tokens(task_settings, max_output_tokens)
        self._iteration = 0

    def run(self) -> str:
        while True:
            # Limits are *trigger thresholds*, not hard caps: once we reach one we
            # stop starting new work iterations and make exactly one terminal
            # wind-down call instead of raising.
            if self._iteration_limit_reached():
                self.logger.limit_reached(kind="max_iterations", n=self._iteration, max=self._max_iterations)
                return self._wrap_up("max_iterations")

            self._iteration += 1
            self.logger.iteration(n=self._iteration, max=self._max_iterations)
            self.logger.prompt(messages=self.context.messages, tools=self.context.tools)

            response = self.client.call(**self._call_opts())
            self.logger.raw(data=response)
            parsed = self.builder.parse_response(response)

            if parsed["stop_reason"] == "tool_use":
                self._handle_tool_calls(parsed["content"], response)
            else:
                text = self._extract_text(parsed["content"])
                self._log_response(text=text, response=response)
                self.logger.turn_end(reason="completed", iterations=self._iteration)
                self.context.add_message("assistant", text)
                return text

    def _resolve_max_iterations(self, task_settings: dict[str, Any] | None, explicit: int | None) -> int:
        if explicit is not None:
            return int(explicit)
        if task_settings and hasattr(self.context.task, "max_iterations"):
            return self.context.task.max_iterations(task_settings)
        return self.MAX_ITERATIONS

    def _resolve_max_output_tokens(self, task_settings: dict[str, Any] | None, explicit: int | None) -> int | None:
        if explicit is not None:
            return explicit
        if task_settings and hasattr(self.context.task, "max_output_tokens"):
            return self.context.task.max_output_tokens(task_settings)
        return None

    def _iteration_limit_reached(self) -> bool:
        return self._max_iterations > 0 and self._iteration >= self._max_iterations

    # Per-call options shared by every model round-trip of the turn.
    def _call_opts(self) -> dict[str, Any]:
        return {"max_output_tokens": self._max_output_tokens} if self._max_output_tokens else {}

    # One final, tools-disabled model call so the agent ends the turn in
    # character rather than aborting. Runs *outside* the counted loop: it never
    # re-checks the limits (so it cannot re-trigger) and does not increment
    # self._iteration. Falls back to a deterministic message if the call fails.
    def _wrap_up(self, reason: str) -> str:
        self.context.add_message("user", self.WRAP_UP_DIRECTIVE)
        try:
            response = self.client.call(tools=[], max_output_tokens=self.WRAP_UP_OUTPUT_TOKENS)
        except ApiError:
            msg = self._fallback_message(reason)
            self.logger.turn_end(reason=reason, iterations=self._iteration)
            self.context.add_message("assistant", msg)
            return msg

        text = self._extract_text(self.builder.parse_response(response)["content"])
        if not text.strip():
            text = self._fallback_message(reason)
        self._log_response(text=text, response=response)
        self.logger.turn_end(reason=reason, iterations=self._iteration)
        self.context.add_message("assistant", text)
        return text

    def _fallback_message(self, reason: str) -> str:
        return (
            f"I reached my {self._max_iterations}-action limit for this turn before finishing "
            f"({reason}). Ask me to continue and I'll pick up from here."
        )

    @staticmethod
    def _extract_text(content: list[dict[str, Any]]) -> str:
        return "".join(b["text"] for b in content if b.get("type") == "text")

    def _handle_tool_calls(self, content: list[dict[str, Any]], response: dict[str, Any]) -> None:
        tool_calls = [b for b in content if b.get("type") == "tool_use"]

        reasoning = self._extract_text(content)
        if reasoning.strip():
            reasoning_text = reasoning
        else:
            n = len(tool_calls)
            reasoning_text = f"(tool use — {n} call{'s' if n != 1 else ''})"
        self._log_response(text=reasoning_text, response=response)

        self.context.add_message("assistant", content)

        for block in tool_calls:
            name = block["name"]
            args = block["input"]
            use_id = block["id"]

            self.logger.tool_call(name=name, args=args)
            try:
                result = self.registry.dispatch(name, args)
                self.logger.tool_result(name=name, result=result, ok=True)
            except Exception as e:  # noqa: BLE001
                result = f"ERROR: {type(e).__name__}: {e}"
                self.logger.tool_result(name=name, result=result, ok=False, error=str(e))

            self.context.add_message("tool_result", str(result), tool_use_id=use_id)

    def _log_response(self, *, text: str, response: dict[str, Any]) -> None:
        self.logger.response(
            text=text,
            usage=self._normalized_usage(response),
            stop_reason=response.get("stop_reason"),
            task=self.context.task,
            backend=self.builder.backend,
        )

    @staticmethod
    def _normalized_usage(response: dict[str, Any]) -> dict[str, Any] | None:
        if response.get("usage"):
            return response["usage"]
        if response.get("usageMetadata"):
            return response["usageMetadata"]

        usage = {key: response[key] for key in ("prompt_eval_count", "eval_count") if key in response}
        return usage or None
