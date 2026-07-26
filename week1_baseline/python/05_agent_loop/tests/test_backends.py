import json

import pytest

from boukensha.backends.anthropic import Anthropic
from boukensha.backends.gemini import Gemini
from boukensha.backends.ollama import Ollama
from boukensha.backends.ollama_cloud import OllamaCloud
from boukensha.backends.openai import OpenAI
from boukensha.context import Context
from boukensha.errors import UnsupportedModelError
from boukensha.tool import Tool


def make_context(*, with_tools: bool = True) -> Context:
    ctx = Context(task=None, system="You are a MUD player assistant.")
    if with_tools:
        ctx.register_tool(
            Tool(
                "move",
                "Move the player in a direction (north, south, east, west, up, down)",
                {"direction": {"type": "string", "description": "The direction to move"}},
                lambda *, direction: direction,
            )
        )
    ctx.add_message("user", "Explore north.")
    ctx.add_message("assistant", "Sure.")
    ctx.add_message("tool_result", "A corridor.", tool_use_id="toolu_01X")
    return ctx


# ---------- model validation / cost estimation (shared Base behavior) ------


def test_validate_model_returns_known_model():
    assert Anthropic.validate_model("claude-haiku-4-5") == "claude-haiku-4-5"


def test_validate_model_raises_for_unknown_model():
    with pytest.raises(UnsupportedModelError, match="Anthropic does not support model 'nope'"):
        Anthropic.validate_model("nope")


def test_estimate_cost_computes_from_token_counts():
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")

    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) == 6.0


def test_estimate_cost_is_zero_not_none_for_free_local_models():
    backend = Ollama(model="gemma4")

    assert backend.estimate_cost(input_tokens=1_000, output_tokens=1_000) == 0.0


def test_estimate_cost_is_none_when_pricing_is_unknown():
    backend = OllamaCloud(api_key="key", model="kimi-k2.5:cloud")

    assert backend.estimate_cost(input_tokens=1_000, output_tokens=1_000) is None


def test_usage_level_defaults_to_none_when_absent():
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")

    assert backend.usage_level is None


def test_usage_level_present_for_ollama_cloud():
    backend = OllamaCloud(api_key="key", model="kimi-k2.5:cloud")

    assert backend.usage_level == "high"


# ---------- Anthropic -------------------------------------------------------


def test_anthropic_to_messages_wraps_tool_result():
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")

    messages = backend.to_messages(make_context().messages)

    assert messages[0] == {"role": "user", "content": "Explore north."}
    assert messages[2] == {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": "toolu_01X", "content": "A corridor."}],
    }


def test_anthropic_to_payload_has_top_level_system():
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")

    payload = backend.to_payload(make_context())

    assert payload["system"] == "You are a MUD player assistant."
    assert payload["max_tokens"] == 1024
    assert payload["tools"][0]["input_schema"]["required"] == ["direction"]


def test_anthropic_headers_and_url():
    backend = Anthropic(api_key="secret", model="claude-haiku-4-5")

    assert backend.headers["x-api-key"] == "secret"
    assert backend.url == "https://api.anthropic.com/v1/messages"


def test_anthropic_to_payload_tools_override_bypasses_to_tools():
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")

    payload = backend.to_payload(make_context(), tools=[])

    assert payload["tools"] == []


def test_anthropic_parse_response_end_turn():
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")
    response = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Sure."}]}

    assert backend.parse_response(response) == {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "Sure."}],
    }


def test_anthropic_parse_response_tool_use():
    backend = Anthropic(api_key="key", model="claude-haiku-4-5")
    response = {
        "stop_reason": "tool_use",
        "content": [{"type": "tool_use", "id": "toolu_01X", "name": "move", "input": {"direction": "north"}}],
    }

    parsed = backend.parse_response(response)

    assert parsed["stop_reason"] == "tool_use"
    assert parsed["content"][0]["id"] == "toolu_01X"


# ---------- Gemini -----------------------------------------------------------


def test_gemini_renames_assistant_role_to_model():
    backend = Gemini(api_key="key", model="gemini-2.5-flash")

    messages = backend.to_messages(make_context().messages)

    assert messages[1] == {"role": "model", "parts": [{"text": "Sure."}]}


def test_gemini_tool_result_becomes_function_response():
    backend = Gemini(api_key="key", model="gemini-2.5-flash")

    messages = backend.to_messages(make_context().messages)

    assert messages[2] == {
        "role": "user",
        "parts": [{"functionResponse": {"name": "toolu_01X", "response": {"content": "A corridor."}}}],
    }


def test_gemini_to_tools_empty_list_when_no_tools():
    backend = Gemini(api_key="key", model="gemini-2.5-flash")

    assert backend.to_tools(make_context(with_tools=False).tools) == []


def test_gemini_to_payload_uses_system_instruction_and_contents():
    backend = Gemini(api_key="key", model="gemini-2.5-flash")

    payload = backend.to_payload(make_context())

    assert payload["systemInstruction"] == {"parts": [{"text": "You are a MUD player assistant."}]}
    assert "contents" in payload
    assert payload["generationConfig"] == {"maxOutputTokens": 1024}


def test_gemini_url_interpolates_model():
    backend = Gemini(api_key="key", model="gemini-2.5-flash")

    assert backend.url == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def test_gemini_parse_response_text_only():
    backend = Gemini(api_key="key", model="gemini-2.5-flash")
    response = {"candidates": [{"content": {"parts": [{"text": "Sure."}]}}]}

    assert backend.parse_response(response) == {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Sure."}]}


def test_gemini_parse_response_tool_use_reuses_name_as_id():
    backend = Gemini(api_key="key", model="gemini-2.5-flash")
    response = {
        "candidates": [{"content": {"parts": [{"functionCall": {"name": "move", "args": {"direction": "north"}}}]}}]
    }

    parsed = backend.parse_response(response)

    assert parsed["stop_reason"] == "tool_use"
    assert parsed["content"] == [{"type": "tool_use", "id": "move", "name": "move", "input": {"direction": "north"}}]


def test_gemini_to_messages_rebuilds_function_call_from_list_content():
    backend = Gemini(api_key="key", model="gemini-2.5-flash")
    ctx = make_context()
    ctx.add_message("assistant", [{"type": "tool_use", "id": "move", "name": "move", "input": {"direction": "north"}}])

    messages = backend.to_messages(ctx.messages)

    assert messages[-1] == {"role": "model", "parts": [{"functionCall": {"name": "move", "args": {"direction": "north"}}}]}


# ---------- Ollama / OllamaCloud / OpenAI (system + messages, function-wrapped tools) --


def test_ollama_to_messages_prepends_system_and_uses_tool_name():
    backend = Ollama(model="gemma4")

    messages = backend.to_messages("You are a MUD player assistant.", make_context().messages)

    assert messages[0] == {"role": "system", "content": "You are a MUD player assistant."}
    assert messages[-1] == {"role": "tool", "tool_name": "toolu_01X", "content": "A corridor."}


def test_ollama_to_payload_has_no_max_output_tokens_field():
    backend = Ollama(model="gemma4")

    payload = backend.to_payload(make_context())

    assert payload["stream"] is False
    assert "max_output_tokens" not in payload
    assert "max_tokens" not in payload


def test_ollama_url_uses_configured_host():
    backend = Ollama(host="http://example:1234", model="gemma4")

    assert backend.url == "http://example:1234/api/chat"


def test_ollama_cloud_headers_include_bearer_token():
    backend = OllamaCloud(api_key="secret", model="kimi-k2.5:cloud")

    assert backend.headers["Authorization"] == "Bearer secret"


def test_openai_to_messages_uses_tool_call_id():
    backend = OpenAI(api_key="key", model="gpt-5.4-mini")

    messages = backend.to_messages("You are a MUD player assistant.", make_context().messages)

    assert messages[-1] == {"role": "tool", "tool_call_id": "toolu_01X", "content": "A corridor."}


def test_openai_to_payload_uses_max_completion_tokens():
    backend = OpenAI(api_key="key", model="gpt-5.4-mini")

    payload = backend.to_payload(make_context())

    assert payload["max_completion_tokens"] == 1024


def test_openai_and_ollama_to_tools_use_function_wrapper():
    ollama_tools = Ollama(model="gemma4").to_tools(make_context().tools)
    openai_tools = OpenAI(api_key="key", model="gpt-5.4-mini").to_tools(make_context().tools)

    assert ollama_tools[0]["type"] == "function"
    assert ollama_tools[0]["function"]["name"] == "move"
    assert openai_tools[0]["type"] == "function"


# ---------- parse_response / assistant_message (Ollama, Ollama Cloud, OpenAI) ----------


def test_ollama_parse_response_text_only():
    backend = Ollama(model="gemma4")
    response = {"message": {"content": "Sure.", "tool_calls": []}}

    assert backend.parse_response(response) == {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Sure."}]}


def test_ollama_parse_response_tool_use_reuses_name_as_id():
    backend = Ollama(model="gemma4")
    response = {
        "message": {"content": "", "tool_calls": [{"function": {"name": "move", "arguments": {"direction": "north"}}}]}
    }

    parsed = backend.parse_response(response)

    assert parsed["stop_reason"] == "tool_use"
    assert parsed["content"] == [{"type": "tool_use", "id": "move", "name": "move", "input": {"direction": "north"}}]


def test_ollama_to_messages_rebuilds_tool_calls_from_list_content():
    backend = Ollama(model="gemma4")
    ctx = make_context()
    ctx.add_message("assistant", [{"type": "tool_use", "id": "move", "name": "move", "input": {"direction": "north"}}])

    messages = backend.to_messages("You are a MUD player assistant.", ctx.messages)

    assert messages[-1] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "move", "arguments": {"direction": "north"}}}],
    }


def test_ollama_cloud_parse_response_and_assistant_message_match_ollama_shape():
    backend = OllamaCloud(api_key="key", model="kimi-k2.5:cloud")
    response = {
        "message": {"content": "", "tool_calls": [{"function": {"name": "move", "arguments": {"direction": "north"}}}]}
    }

    parsed = backend.parse_response(response)
    ctx = make_context()
    ctx.add_message("assistant", parsed["content"])
    messages = backend.to_messages("You are a MUD player assistant.", ctx.messages)

    assert parsed["stop_reason"] == "tool_use"
    assert messages[-1]["tool_calls"] == [{"function": {"name": "move", "arguments": {"direction": "north"}}}]


def test_openai_parse_response_text_only():
    backend = OpenAI(api_key="key", model="gpt-5.4-mini")
    response = {"choices": [{"message": {"content": "Sure.", "tool_calls": []}}]}

    assert backend.parse_response(response) == {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Sure."}]}


def test_openai_parse_response_decodes_json_string_arguments():
    backend = OpenAI(api_key="key", model="gpt-5.4-mini")
    response = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "move", "arguments": '{"direction": "north"}'}}
                    ],
                }
            }
        ]
    }

    parsed = backend.parse_response(response)

    assert parsed["stop_reason"] == "tool_use"
    assert parsed["content"] == [
        {"type": "tool_use", "id": "call_1", "name": "move", "input": {"direction": "north"}}
    ]


def test_openai_to_messages_reencodes_input_as_json_string_arguments():
    backend = OpenAI(api_key="key", model="gpt-5.4-mini")
    ctx = make_context()
    ctx.add_message(
        "assistant", [{"type": "tool_use", "id": "call_1", "name": "move", "input": {"direction": "north"}}]
    )

    messages = backend.to_messages("You are a MUD player assistant.", ctx.messages)
    rebuilt_call = messages[-1]["tool_calls"][0]

    assert rebuilt_call["id"] == "call_1"
    assert rebuilt_call["type"] == "function"
    assert json.loads(rebuilt_call["function"]["arguments"]) == {"direction": "north"}
