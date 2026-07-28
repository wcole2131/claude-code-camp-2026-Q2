import os
from collections.abc import Callable
from pathlib import Path
from typing import cast

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
from .message import Message
from .prompt_builder import PromptBuilder
from .registry import Registry
from .repl import Repl
from .run_dsl import RunDSL
from .tasks.player import Player
from .tool import Tool
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
    "Message",
    "Ollama",
    "OllamaCloud",
    "OpenAI",
    "Player",
    "PromptBuilder",
    "Registry",
    "Repl",
    "RunDSL",
    "Tool",
    "UnknownToolError",
    "UnsupportedModelError",
    "debug",
    "get_config",
    "is_debug",
    "is_quiet",
    "loud",
    "quiet",
    "repl",
    "run",
]

_quiet = False
_debug = False
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def quiet() -> None:
    global _quiet
    _quiet = True


def loud() -> None:
    global _quiet
    _quiet = False


def is_quiet() -> bool:
    return _quiet


def debug() -> None:
    global _debug
    _debug = True


def is_debug() -> bool:
    return _debug


def run(
    *,
    task: str,
    system: str | None = None,
    model: str | None = None,
    backend: str | None = None,
    api_key: str | None = None,
    ollama_host: str = "http://localhost:11434",
    log: str | Path | None = None,
    max_output_tokens: int | None = None,
    configure: Callable[[RunDSL], None] | None = None,
) -> str:
    cfg = get_config()
    task_class = Player
    task_settings = cfg.tasks(task_class.task_name())
    system = system or task_class.system_prompt(
        task_settings, user_prompts_dir=cfg.user_prompts_dir, default_prompts_dir=Config.PROMPTS_DIR
    )
    model = model or task_class.model(task_settings)
    backend = backend or task_class.provider(task_settings)
    api_key = api_key or {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
        "gemini": os.environ.get("GEMINI_API_KEY"),
        "ollama_cloud": os.environ.get("OLLAMA_API_KEY"),
    }.get(backend)

    ctx = Context(task=task_class, system=system)
    registry = Registry(ctx)

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
        effective_max_iterations = task_class.max_iterations(task_settings)
        effective_max_output_tokens = max_output_tokens or task_class.max_output_tokens(task_settings)

        logger = Logger(
            log=log,
            snapshot={
                "task": task_class.task_name(),
                "max_iterations": effective_max_iterations,
                "max_output_tokens": effective_max_output_tokens,
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
            task_settings=task_settings,
            max_iterations=effective_max_iterations,
            max_output_tokens=effective_max_output_tokens,
        )

        ctx.add_message("user", task)
        return agent.run()
    finally:
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
    max_output_tokens: int | None = None,
    configure: Callable[[RunDSL], None] | None = None,
) -> None:
    cfg = get_config()
    task_class = Player
    task_settings = cfg.tasks(task_class.task_name())
    system = system or task_class.system_prompt(
        task_settings, user_prompts_dir=cfg.user_prompts_dir, default_prompts_dir=Config.PROMPTS_DIR
    )
    model = model or task_class.model(task_settings)
    backend = backend or task_class.provider(task_settings)
    api_key = api_key or {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
        "gemini": os.environ.get("GEMINI_API_KEY"),
        "ollama_cloud": os.environ.get("OLLAMA_API_KEY"),
    }.get(backend)

    ctx = Context(task=task_class, system=system)
    registry = Registry(ctx)

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
        effective_max_iterations = task_class.max_iterations(task_settings)
        effective_max_output_tokens = max_output_tokens or task_class.max_output_tokens(task_settings)

        logger = Logger(
            log=log,
            snapshot={
                "task": task_class.task_name(),
                "max_iterations": effective_max_iterations,
                "max_output_tokens": effective_max_output_tokens,
                "model": model,
                "provider": backend,
            },
        )

        try:
            Repl(
                context=ctx,
                registry=registry,
                builder=builder,
                client=client,
                logger=logger,
                task_settings=task_settings,
                max_iterations=effective_max_iterations,
                max_output_tokens=effective_max_output_tokens,
                config_dir=cfg.dir,
                provider=backend,
                model=model,
                version=VERSION,
                api_key=api_key,
            ).start()
        except KeyboardInterrupt:
            print("\nInterrupted.")
    finally:
        if logger is not None:
            logger.close()
