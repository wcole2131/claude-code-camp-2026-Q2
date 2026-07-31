from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .agent import Agent
from .errors import ApiError, LoopError

if TYPE_CHECKING:
    import threading
    from collections.abc import Callable
    from pathlib import Path

    from .client import Client
    from .context import Context
    from .logger import Logger
    from .prompt_builder import PromptBuilder
    from .registry import Registry


class Repl:
    """The interactive session loop.

    It wraps the same primitives as a single boukensha.run call, but instead of
    running once it stays alive: it reads a task from the user, runs the agent,
    prints the reply, and loops back to the prompt.

    The Context is shared across every turn so conversation history accumulates
    naturally -- the agent sees the full transcript each time it is called.

    Built-in commands (not sent to the agent):
      /help    print the command list
      /clear   wipe conversation history (tools stay registered)
      /exit    leave the REPL
      /quit    alias for /exit

    Repl no longer hard-codes stdout/stdin: on_output(callback) routes every
    string it would otherwise print through the callback instead, and
    handle_command/run_turn are public so an alternate front-end (Tui) can
    drive the session without going through start()'s own input loop.
    """

    PROMPT = "boukensha> "

    HELP = (
        "Commands:\n"
        "  /clear   wipe conversation history (tools stay)\n"
        "  /exit    leave the REPL\n"
        "  /help    show this message"
    )

    def __init__(
        self,
        *,
        context: Context,
        registry: Registry,
        builder: PromptBuilder,
        client: Client,
        logger: Logger,
        config_dir: Path | None = None,
        provider: str | None = None,
        model: str | None = None,
        version: str | None = None,
        api_key: str | None = None,
        task_settings: dict[str, Any] | None = None,
        max_iterations: int | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self._context = context
        self._registry = registry
        self._builder = builder
        self._client = client
        self._logger = logger
        self._task_settings = task_settings
        self._max_iterations = max_iterations
        self._max_output_tokens = max_output_tokens
        self._config_dir = config_dir
        self._provider = provider
        self._model = model
        self._version = version
        self._api_key = api_key
        self._turn = 0
        self._output_cb: Callable[[str], None] | None = None

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def context(self) -> Context:
        return self._context

    @property
    def model(self) -> str | None:
        return self._model

    @property
    def version(self) -> str | None:
        return self._version

    def on_output(self, callback: Callable[[str], None]) -> None:
        """Route every string this Repl would otherwise print through callback
        instead. Used by Tui so it can append REPL output into its own
        scrollable conversation viewport rather than stdout."""
        self._output_cb = callback

    def start(self) -> None:
        self._output(self.banner())

        while True:
            try:
                line = input(self.PROMPT)
            except EOFError:
                break

            line = line.strip()
            if not line:
                continue

            result = self.handle_command(line)
            if result == "quit":
                break
            if result == "command":
                continue

            self.run_turn(line)

    def banner(self) -> str:
        key_status = (
            "✗ API key not set" if not self._api_key or not self._api_key.strip() else "✓ API key set"
        )
        provider_line = f"{self._provider or 'default'} ({self._model or 'default'})  {key_status}"
        config_exists = self._config_dir is not None and self._config_dir.is_dir()
        config_line = (
            str(self._config_dir) if config_exists else f"{self._config_dir or '(default)'}  ✗ directory not found"
        )
        ver = self._version or "?.?.?"

        return (
            "\n".join(
                [
                    "",
                    "╔══════════════════════════════════════╗",
                    f"║  BOUKENSHA MUD Assistant (v{ver}){' ' * (9 - len(ver))}║",
                    "╚══════════════════════════════════════╝",
                    f"  config:    {config_line}",
                    f"  provider:  {provider_line}",
                    f"  tools:     {self._context.tool_count} registered (via MCP — see mcp_servers:)",
                    "",
                    "  /clear           reset conversation history",
                    "  /exit or /quit    leave the REPL",
                ]
            )
            + "\n\n"
        )

    def handle_command(self, line: str) -> str | None:
        """Handle a slash command. Returns "quit", "command", or None (not a
        command -- the caller should treat `line` as a turn to run)."""
        match line:
            case "/exit" | "/quit":
                self._output("Goodbye.")
                return "quit"
            case "/help":
                self._output(self.HELP)
                return "command"
            case "/clear":
                self._context.clear_messages()
                self._turn = 0
                self._output("(conversation history cleared)")
                return "command"
            case _:
                return None

    def run_turn(self, line: str, *, interrupt: threading.Event | None = None) -> None:
        self._turn += 1
        self._logger.turn(n=self._turn)

        self._context.add_message("user", line)

        agent = Agent(
            context=self._context,
            registry=self._registry,
            builder=self._builder,
            client=self._client,
            logger=self._logger,
            task_settings=self._task_settings,
            max_iterations=self._max_iterations,
            max_output_tokens=self._max_output_tokens,
            interrupt=interrupt,
        )
        try:
            result = agent.run()
        except LoopError as e:
            self._output(f"\n[error] {e}")
            return
        except ApiError as e:
            self._output(f"\n[error] API call failed: {e}")
            return

        self._output("")
        self._output(result)

    def _output(self, s: str = "") -> None:
        if self._output_cb is not None:
            self._output_cb(str(s))
        else:
            print(str(s))
