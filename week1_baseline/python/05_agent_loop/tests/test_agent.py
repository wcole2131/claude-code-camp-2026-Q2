from unittest.mock import MagicMock

from boukensha.agent import Agent
from boukensha.errors import ApiError


def make_agent(*, max_iterations=None, max_output_tokens=None, task_settings=None, context=None):
    context = context if context is not None else MagicMock()
    registry = MagicMock()
    builder = MagicMock()
    builder.parse_response.side_effect = lambda response: response
    client = MagicMock()
    agent = Agent(
        context=context,
        registry=registry,
        builder=builder,
        client=client,
        task_settings=task_settings,
        max_iterations=max_iterations,
        max_output_tokens=max_output_tokens,
    )
    return agent, context, registry, builder, client


def test_end_turn_on_first_response_returns_text_immediately():
    agent, _context, registry, _builder, client = make_agent(max_iterations=5)
    client.call.return_value = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done."}]}

    result = agent.run()

    assert result == "Done."
    client.call.assert_called_once()
    registry.dispatch.assert_not_called()


def test_tool_call_round_trip_stores_assistant_message_and_dispatches_tool():
    agent, context, registry, _builder, client = make_agent(max_iterations=5)
    tool_block = {"type": "tool_use", "id": "toolu_1", "name": "move", "input": {"direction": "north"}}
    client.call.side_effect = [
        {"stop_reason": "tool_use", "content": [tool_block]},
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done."}]},
    ]
    registry.dispatch.return_value = "You move north."

    result = agent.run()

    assert result == "Done."
    registry.dispatch.assert_called_once_with("move", {"direction": "north"})
    # The assistant message stores the raw block list, not a string.
    context.add_message.assert_any_call("assistant", [tool_block])
    # The tool_result message stores the FULL untruncated string.
    context.add_message.assert_any_call("tool_result", "You move north.", tool_use_id="toolu_1")


def test_tool_result_print_preview_is_truncated_but_stored_message_is_not(capsys):
    agent, context, registry, _builder, client = make_agent(max_iterations=5)
    long_result = "x" * 100
    tool_block = {"type": "tool_use", "id": "toolu_1", "name": "read_file", "input": {"path": "README.md"}}
    client.call.side_effect = [
        {"stop_reason": "tool_use", "content": [tool_block]},
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done."}]},
    ]
    registry.dispatch.return_value = long_result

    agent.run()

    context.add_message.assert_any_call("tool_result", long_result, tool_use_id="toolu_1")
    captured = capsys.readouterr()
    assert ("x" * 61) in captured.out
    assert ("x" * 100) not in captured.out


def test_multiple_tool_calls_in_one_turn_are_all_dispatched():
    agent, _context, registry, _builder, client = make_agent(max_iterations=5)
    blocks = [
        {"type": "tool_use", "id": "1", "name": "look", "input": {}},
        {"type": "tool_use", "id": "2", "name": "move", "input": {"direction": "north"}},
    ]
    client.call.side_effect = [
        {"stop_reason": "tool_use", "content": blocks},
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done."}]},
    ]
    registry.dispatch.return_value = "ok"

    agent.run()

    assert registry.dispatch.call_count == 2


def test_reaching_max_iterations_triggers_wrap_up_without_calling_client_again():
    agent, _context, registry, _builder, client = make_agent(max_iterations=1)
    # Every call returns a tool_use response, so the loop would otherwise never stop.
    tool_block = {"type": "tool_use", "id": "1", "name": "move", "input": {}}
    client.call.side_effect = [
        {"stop_reason": "tool_use", "content": [tool_block]},  # iteration 1
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Wrapped up."}]},  # wind-down call
    ]
    registry.dispatch.return_value = "ok"

    result = agent.run()

    assert result == "Wrapped up."
    assert client.call.call_count == 2
    # The wind-down call disables tools and uses the fixed wind-down token budget,
    # bypassing whatever max_output_tokens was configured for normal turns.
    _, kwargs = client.call.call_args_list[1]
    assert kwargs == {"tools": [], "max_output_tokens": Agent.WRAP_UP_OUTPUT_TOKENS}


def test_wrap_up_falls_back_to_deterministic_message_on_blank_response():
    agent, _context, _registry, _builder, client = make_agent(max_iterations=5)
    client.call.return_value = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "   "}]}

    result = agent._wrap_up("max_iterations")

    assert "reached my" in result
    assert "max_iterations" in result


def test_wrap_up_falls_back_to_deterministic_message_on_api_error():
    agent, _context, _registry, _builder, client = make_agent(max_iterations=5)
    client.call.side_effect = ApiError("boom")

    result = agent._wrap_up("max_iterations")

    assert "reached my" in result


def test_max_iterations_zero_disables_the_ceiling():
    agent, _context, _registry, _builder, client = make_agent(max_iterations=0)
    client.call.return_value = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done."}]}

    result = agent.run()

    assert result == "Done."
    client.call.assert_called_once()


def test_explicit_max_output_tokens_is_forwarded_to_normal_calls():
    agent, _context, _registry, _builder, client = make_agent(max_iterations=5, max_output_tokens=2048)
    client.call.return_value = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done."}]}

    agent.run()

    client.call.assert_called_once_with(max_output_tokens=2048)


def test_no_max_output_tokens_means_call_gets_no_kwargs():
    agent, _context, _registry, _builder, client = make_agent(max_iterations=5)
    client.call.return_value = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done."}]}

    agent.run()

    client.call.assert_called_once_with()


def test_task_settings_resolution_delegates_to_the_task_class():
    class FakeTask:
        @classmethod
        def max_iterations(cls, settings):
            return 3

        @classmethod
        def max_output_tokens(cls, settings):
            return 555

    context = MagicMock()
    context.task = FakeTask
    agent, _context, _registry, _builder, _client = make_agent(
        context=context, task_settings={"max_iterations": 3, "max_output_tokens": 555}
    )

    assert agent._max_iterations == 3
    assert agent._max_output_tokens == 555


def test_explicit_max_iterations_wins_over_task_settings():
    class FakeTask:
        @classmethod
        def max_iterations(cls, settings):
            return 3

    context = MagicMock()
    context.task = FakeTask
    agent, _context, _registry, _builder, _client = make_agent(
        context=context, task_settings={"max_iterations": 3}, max_iterations=10
    )

    assert agent._max_iterations == 10
