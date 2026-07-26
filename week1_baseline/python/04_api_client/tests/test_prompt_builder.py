import pytest

from boukensha.backends.anthropic import Anthropic
from boukensha.backends.ollama import Ollama
from boukensha.context import Context
from boukensha.prompt_builder import PromptBuilder
from boukensha.tool import Tool


def make_context() -> Context:
    ctx = Context(task=None, system="You are a MUD player assistant.")
    ctx.register_tool(Tool("move", "Move", {"direction": {"type": "string"}}, lambda *, direction: direction))
    ctx.add_message("user", "Explore north.")
    return ctx


def test_to_api_payload_delegates_to_backend():
    ctx = make_context()
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")
    builder = PromptBuilder(ctx, backend)

    payload = builder.to_api_payload()

    assert payload == backend.to_payload(ctx)


def test_to_api_payload_forwards_max_output_tokens():
    ctx = make_context()
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")
    builder = PromptBuilder(ctx, backend)

    payload = builder.to_api_payload(max_output_tokens=256)

    assert payload["max_tokens"] == 256


def test_headers_and_url_delegate_to_backend():
    ctx = make_context()
    backend = Anthropic(api_key="secret", model="claude-haiku-4-5")
    builder = PromptBuilder(ctx, backend)

    assert builder.headers == backend.headers
    assert builder.url == backend.url


def test_to_tools_delegates_to_backend():
    ctx = make_context()
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")
    builder = PromptBuilder(ctx, backend)

    assert builder.to_tools() == backend.to_tools(ctx.tools)


def test_to_messages_works_for_single_arg_backends():
    ctx = make_context()
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")
    builder = PromptBuilder(ctx, backend)

    assert builder.to_messages() == backend.to_messages(ctx.messages)


def test_to_messages_raises_for_two_arg_backends():
    # Matches the Ruby source's own latent bug: PromptBuilder#to_messages always calls
    # the backend with one argument, but Ollama/OllamaCloud/OpenAI's to_messages needs
    # (system, messages). This is never hit via to_api_payload (which calls the
    # backend's to_payload directly, using the correct arity internally) -- only a
    # direct PromptBuilder.to_messages() call surfaces it. Ported faithfully rather
    # than silently fixed; see docs/plans/python_port/03_prompt_builder.md.
    ctx = make_context()
    backend = Ollama(model="gemma4")
    builder = PromptBuilder(ctx, backend)

    with pytest.raises(TypeError):
        builder.to_messages()
