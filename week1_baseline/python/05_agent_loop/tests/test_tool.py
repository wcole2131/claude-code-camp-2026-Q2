from boukensha.tool import Tool


def make_tool(description: str) -> Tool:
    return Tool("move", description, {"direction": {"type": "string"}}, lambda direction: direction)


def test_str_shows_name_and_params():
    tool = make_tool("Move the player")

    assert str(tool) == "#<Tool name=move description=Move the player params=['direction']>"


def test_str_truncates_description_to_41_chars():
    description = "x" * 60

    tool = make_tool(description)

    assert str(tool) == f"#<Tool name=move description={'x' * 41} params=['direction']>"


def test_str_does_not_truncate_short_description():
    description = "x" * 41

    tool = make_tool(description)

    assert str(tool) == f"#<Tool name=move description={description} params=['direction']>"


def test_params_reflects_parameter_keys_not_values():
    tool = Tool("say", "Say something", {"message": {"type": "string"}}, lambda message: message)

    assert str(tool) == "#<Tool name=say description=Say something params=['message']>"


def test_block_is_callable():
    tool = make_tool("Move")

    assert tool.block("north") == "north"
