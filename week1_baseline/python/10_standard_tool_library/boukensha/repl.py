from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Deferred, whole-module import (not `from . import quiet, loud`) is required here for the same
# reason logger.py does it: boukensha/__init__.py imports this module before it defines
# quiet/loud in its own namespace, so those attributes must be read lazily, inside method bodies.
import boukensha

from .agent import Agent
from .errors import ApiError, LoopError

if TYPE_CHECKING:
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
      /quiet   suppress detailed logging
      /loud    re-enable logging
      /clear   wipe conversation history (tools stay registered)
      /exit    leave the REPL
      /quit    alias for /exit
    """

    PROMPT = "boukensha> "

    HELP = (
        "Commands:\n"
        "  /quiet   suppress logging output\n"
        "  /loud    re-enable logging output\n"
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

    def start(self) -> None:
        print(self._banner(), end="")

        while True:
            try:
                line = input(self.PROMPT)
            except EOFError:
                break

            line = line.strip()
            if not line:
                continue

            match line:
                case "/exit" | "/quit":
                    print("Goodbye.")
                    break
                case "/help":
                    print(self.HELP)
                    continue
                case "/quiet":
                    boukensha.quiet()
                    print("(logging suppressed — type /loud to re-enable)")
                    continue
                case "/loud":
                    boukensha.loud()
                    print("(logging enabled)")
                    continue
                case "/clear":
                    self._context.clear_messages()
                    self._turn = 0
                    print("(conversation history cleared)")
                    continue

            self._run_turn(line)

    def _banner(self) -> str:
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
                    "  /quiet or /loud   toggle logging",
                    "  /clear           reset conversation history",
                    "  /exit or /quit    leave the REPL",
                ]
            )
            + "\n\n"
        )

    def _run_turn(self, line: str) -> None:
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
        )
        try:
            result = agent.run()
        except LoopError as e:
            print(f"\n[error] {e}")
            return
        except ApiError as e:
            print(f"\n[error] API call failed: {e}")
            return

        print()
        print(result)
