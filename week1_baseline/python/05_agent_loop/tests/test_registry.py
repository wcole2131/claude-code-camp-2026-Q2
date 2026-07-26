import pytest

from boukensha.context import Context
from boukensha.errors import UnknownToolError
from boukensha.registry import Registry
from boukensha.tool import Tool


def test_tool_registers_and_returns_the_tool():
    ctx = Context(task=None)
    registry = Registry(ctx)

    tool = registry.tool(
        "move",
        description="Move the player",
        parameters={"direction": {"type": "string"}},
        block=lambda *, direction: direction,
    )

    assert isinstance(tool, Tool)
    assert tool.name == "move"
    assert ctx.tools["move"] is tool


def test_tool_defaults_parameters_to_empty_dict():
    ctx = Context(task=None)
    registry = Registry(ctx)

    tool = registry.tool("look", description="Look around", block=lambda: "a room")

    assert tool.parameters == {}


def test_dispatch_calls_the_registered_block_with_kwargs():
    ctx = Context(task=None)
    registry = Registry(ctx)
    registry.tool(
        "move",
        description="Move the player",
        parameters={"direction": {"type": "string"}},
        block=lambda *, direction: f"You move {direction}.",
    )

    result = registry.dispatch("move", {"direction": "north"})

    assert result == "You move north."


def test_dispatch_defaults_args_to_empty_dict():
    ctx = Context(task=None)
    registry = Registry(ctx)
    registry.tool("look", description="Look around", block=lambda: "a room")

    assert registry.dispatch("look") == "a room"


def test_dispatch_raises_unknown_tool_error_for_unregistered_name():
    ctx = Context(task=None)
    registry = Registry(ctx)

    with pytest.raises(UnknownToolError, match="No tool registered as 'flee'"):
        registry.dispatch("flee")
