from boukensha.message import Message


def test_str_without_tool_use_id():
    message = Message("user", "Explore north.")

    assert str(message) == "#<Message role=user content=Explore north....>"


def test_str_with_tool_use_id():
    message = Message("tool_result", "You move north.", tool_use_id="toolu_01X")

    assert str(message) == "#<Message role=tool_result [toolu_01X] content=You move north....>"


def test_str_truncates_content_to_61_chars():
    content = "x" * 80

    message = Message("assistant", content)

    assert str(message) == f"#<Message role=assistant content={'x' * 61}...>"


def test_str_does_not_truncate_short_content():
    content = "x" * 61

    message = Message("assistant", content)

    assert str(message) == f"#<Message role=assistant content={content}...>"


def test_content_accepts_a_list_of_blocks():
    content = [{"type": "tool_use", "id": "toolu_01X", "name": "move", "input": {"direction": "north"}}]

    message = Message("assistant", content)

    assert message.content == content
    assert str(message).startswith("#<Message role=assistant content=[{")
