from .agent import Agent
from .backends.anthropic import Anthropic
from .backends.gemini import Gemini
from .backends.ollama import Ollama
from .backends.ollama_cloud import OllamaCloud
from .backends.openai import OpenAI
from .client import Client
from .config import Config
from .context import Context
from .errors import ApiError, UnknownToolError, UnsupportedModelError
from .logger import Logger
from .message import Message
from .prompt_builder import PromptBuilder
from .registry import Registry
from .tasks.player import Player
from .tool import Tool

__all__ = [
    "Agent",
    "Anthropic",
    "ApiError",
    "Client",
    "Config",
    "Context",
    "Gemini",
    "Logger",
    "Message",
    "Ollama",
    "OllamaCloud",
    "OpenAI",
    "Player",
    "PromptBuilder",
    "Registry",
    "Tool",
    "UnknownToolError",
    "UnsupportedModelError",
    "debug",
    "get_config",
    "is_debug",
    "is_quiet",
    "loud",
    "quiet",
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
