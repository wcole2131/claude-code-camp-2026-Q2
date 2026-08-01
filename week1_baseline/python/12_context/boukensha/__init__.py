import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast

from . import models
from .agent import Agent
from .backends.anthropic import Anthropic
from .backends.gemini import Gemini
from .backends.ollama import Ollama
from .backends.ollama_cloud import OllamaCloud
from .backends.openai import OpenAI
from .client import Client
from .config import Config
from .context import Context
from .errors import ApiError, LoopError, UnknownToolError, UnsupportedModelError
from .logger import Logger
from .mcp import MCPClient
from .message import Message
from .prompt_builder import PromptBuilder
from .registry import Registry
from .repl import Repl
from .run_dsl import RunDSL
from .tool import Tool
from .tui import Tui
from .version import VERSION

__all__ = [
    "VERSION",
    "Agent",
    "Anthropic",
    "ApiError",
    "Client",
    "Config",
    "Context",
    "Gemini",
    "Logger",
    "LoopError",
    "MCPClient",
    "Message",
    "Ollama",
    "OllamaCloud",
    "OpenAI",
    "PromptBuilder",
    "Registry",
    "Repl",
    "RunDSL",
    "Tool",
    "Tui",
    "UnknownToolError",
    "UnsupportedModelError",
    "debug",
    "get_config",
    "is_debug",
    "repl",
    "run",
]

_debug = False
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def debug() -> None:
    global _debug
    _debug = True


def is_debug() -> bool:
    return _debug


def _connect_mcp_servers(registry: Registry, specs: list[dict[str, Any]]) -> list[MCPClient]:
    clients = []
    for spec in specs:
        client = MCPClient.connect(**spec)
        client.register_all(registry)
        clients.append(client)
    return clients


def _default_mcp_servers(
    cfg: Config,
    *,
    working_dir: str | Path | Literal[False],
    allowed_commands: list[str] | None,
    shell_timeout: int,
) -> list[dict[str, Any]]:
    servers: list[dict[str, Any]] = []

    if working_dir:
        servers.append(MCPClient.file_system_server(working_dir=working_dir))
        servers.append(
            MCPClient.shell_server(working_dir=working_dir, timeout=shell_timeout, allowed_commands=allowed_commands)
        )

    if cfg.mud_host and cfg.mud_username:
        # Ruby happily passes a nil password through if it's unset (it just fails downstream
        # when the MUD server rejects the login); the cast preserves that same "let it fail
        # downstream" behavior for Python's static typing, same rationale as api_key above.
        servers.append(
            MCPClient.mud_manager_server(
                host=cfg.mud_host, port=cfg.mud_port, name=cfg.mud_username, password=cast(str, cfg.mud_password)
            )
        )

    return servers


def run(
    *,
    task: str,
    system: str | None = None,
    model: str | None = None,
    backend: str | None = None,
    api_key: str | None = None,
    ollama_host: str = "http://localhost:11434",
    log: str | Path | None = None,
    context_window: int | None = None,
    max_output_tokens: int | None = None,
    working_dir: str | Path | Literal[False] | None = None,
    allowed_commands: list[str] | None = None,
    shell_timeout: int = 30,
    mcp_servers: list[dict[str, Any]] | None = None,
    configure: Callable[[RunDSL], None] | None = None,
) -> str:
    cfg = get_config()
    system = system or cfg.system_prompt
    model = model or cfg.model
    context_window = context_window or models.context_window(model)
    backend = backend or cfg.provider_type
    api_key = api_key or {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
        "gemini": os.environ.get("GEMINI_API_KEY"),
        "ollama_cloud": os.environ.get("OLLAMA_API_KEY"),
    }.get(backend)

    if working_dir is None:
        working_dir = Path.cwd()

    ctx = Context(
        system=system, context_window=context_window, working_dir=working_dir,
        compaction_threshold=cfg.agent_compaction_threshold,
    )
    registry = Registry(ctx)

    resolved_servers = (
        mcp_servers
        if mcp_servers is not None
        else _default_mcp_servers(cfg, working_dir=working_dir, allowed_commands=allowed_commands, shell_timeout=shell_timeout)
    )
    mcp_clients = _connect_mcp_servers(registry, resolved_servers)

    if configure is not None:
        configure(RunDSL(registry))

    logger: Logger | None = None
    try:
        # Ruby happily passes a nil api_key through to the backend if the matching env var
        # is unset (it just fails with an auth error later); the cast preserves that same
        # "let it fail downstream" behavior for Python's static typing, which has no dynamic
        # equivalent to declare here.
        match backend:
            case "anthropic":
                be = Anthropic(api_key=cast(str, api_key), model=model)
            case "openai":
                be = OpenAI(api_key=cast(str, api_key), model=model)
            case "gemini":
                be = Gemini(api_key=cast(str, api_key), model=model)
            case "ollama":
                be = Ollama(host=ollama_host, model=model)
            case "ollama_cloud":
                be = OllamaCloud(api_key=cast(str, api_key), model=model)
            case _:
                raise ValueError(
                    f"Unknown backend {backend!r}. Use 'anthropic', 'openai', 'gemini', 'ollama', or 'ollama_cloud'."
                )

        builder = PromptBuilder(ctx, be)
        client = Client(builder)

        logger = Logger(
            log=log,
            snapshot={
                "max_iterations": cfg.agent_max_iterations,
                "max_turn_tokens": cfg.agent_max_turn_tokens,
                "max_output_tokens": max_output_tokens or cfg.agent_max_output_tokens,
                "context_window": context_window,
                "model": model,
                "provider": backend,
            },
        )
        agent = Agent(
            context=ctx,
            registry=registry,
            builder=builder,
            client=client,
            logger=logger,
            max_iterations=cfg.agent_max_iterations,
            max_turn_tokens=cfg.agent_max_turn_tokens,
            max_output_tokens=max_output_tokens or cfg.agent_max_output_tokens,
        )

        ctx.add_message("user", task)
        return agent.run()
    finally:
        for mcp_client in mcp_clients:
            mcp_client.close()
        if logger is not None:
            logger.close()


def repl(
    *,
    system: str | None = None,
    model: str | None = None,
    backend: str | None = None,
    api_key: str | None = None,
    ollama_host: str = "http://localhost:11434",
    log: str | Path | None = None,
    context_window: int | None = None,
    max_output_tokens: int | None = None,
    working_dir: str | Path | Literal[False] | None = None,
    allowed_commands: list[str] | None = None,
    shell_timeout: int = 30,
    mcp_servers: list[dict[str, Any]] | None = None,
    tui: bool = True,
    configure: Callable[[RunDSL], None] | None = None,
) -> None:
    cfg = get_config()
    system = system or cfg.system_prompt
    model = model or cfg.model
    context_window = context_window or models.context_window(model)
    backend = backend or cfg.provider_type
    api_key = api_key or {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
        "gemini": os.environ.get("GEMINI_API_KEY"),
        "ollama_cloud": os.environ.get("OLLAMA_API_KEY"),
    }.get(backend)

    if working_dir is None:
        working_dir = Path.cwd()

    ctx = Context(
        system=system, context_window=context_window, working_dir=working_dir,
        compaction_threshold=cfg.agent_compaction_threshold,
    )
    registry = Registry(ctx)

    resolved_servers = (
        mcp_servers
        if mcp_servers is not None
        else _default_mcp_servers(cfg, working_dir=working_dir, allowed_commands=allowed_commands, shell_timeout=shell_timeout)
    )
    mcp_clients = _connect_mcp_servers(registry, resolved_servers)

    if configure is not None:
        configure(RunDSL(registry))

    logger: Logger | None = None
    try:
        match backend:
            case "anthropic":
                be = Anthropic(api_key=cast(str, api_key), model=model)
            case "openai":
                be = OpenAI(api_key=cast(str, api_key), model=model)
            case "gemini":
                be = Gemini(api_key=cast(str, api_key), model=model)
            case "ollama":
                be = Ollama(host=ollama_host, model=model)
            case "ollama_cloud":
                be = OllamaCloud(api_key=cast(str, api_key), model=model)
            case _:
                raise ValueError(
                    f"Unknown backend {backend!r}. Use 'anthropic', 'openai', 'gemini', 'ollama', or 'ollama_cloud'."
                )

        builder = PromptBuilder(ctx, be)
        client = Client(builder)

        logger = Logger(
            log=log,
            snapshot={
                "max_iterations": cfg.agent_max_iterations,
                "max_turn_tokens": cfg.agent_max_turn_tokens,
                "max_output_tokens": max_output_tokens or cfg.agent_max_output_tokens,
                "context_window": context_window,
                "model": model,
                "provider": backend,
            },
        )

        repl_instance = Repl(
            context=ctx,
            registry=registry,
            builder=builder,
            client=client,
            logger=logger,
            max_iterations=cfg.agent_max_iterations,
            max_turn_tokens=cfg.agent_max_turn_tokens,
            max_output_tokens=max_output_tokens or cfg.agent_max_output_tokens,
            config_dir=cfg.dir,
            provider=backend,
            model=model,
            version=VERSION,
            api_key=api_key,
        )

        try:
            if tui:
                Tui(repl_instance).start()
            else:
                repl_instance.start()
        except KeyboardInterrupt:
            print("\nInterrupted.")
    finally:
        for mcp_client in mcp_clients:
            mcp_client.close()
        if logger is not None:
            logger.close()
