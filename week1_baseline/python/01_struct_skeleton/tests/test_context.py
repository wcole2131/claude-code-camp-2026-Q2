from boukensha.context import Context
from boukensha.tasks.player import Player
from boukensha.tool import Tool


def test_context_starts_empty():
    ctx = Context(task=None)

    assert ctx.tool_count == 0
    assert ctx.turn_count == 0
    assert ctx.messages == []
    assert ctx.tools == {}


def test_register_tool_keys_by_name():
    ctx = Context(task=None)
    tool = Tool("move", "Move", {}, lambda: "")

    ctx.register_tool(tool)

    assert ctx.tools["move"] is tool
    assert ctx.tool_count == 1


def test_add_message_appends_and_defaults_tool_use_id_to_none():
    ctx = Context(task=None)

    ctx.add_message("user", "Explore north.")

    assert ctx.turn_count == 1
    message = ctx.messages[0]
    assert message.role == "user"
    assert message.content == "Explore north."
    assert message.tool_use_id is None


def test_add_message_with_tool_use_id():
    ctx = Context(task=None)

    ctx.add_message("tool_result", "You move north.", tool_use_id="toolu_01X")

    assert ctx.messages[0].tool_use_id == "toolu_01X"


def test_str_with_no_task():
    ctx = Context(task=None)

    assert str(ctx) == "#<Context task=None turns=0 tools=0>"


def test_str_with_task():
    ctx = Context(task=Player, system="You are a MUD player assistant.")
    ctx.register_tool(Tool("move", "Move", {}, lambda: ""))
    ctx.add_message("user", "Explore north.")
    ctx.add_message("assistant", "Sure.")

    assert str(ctx) == "#<Context task=player turns=2 tools=1>"
