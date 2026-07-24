import pytest

from boukensha.tasks.base import Base
from boukensha.tasks.player import Player


def test_base_task_name_not_implemented():
    with pytest.raises(NotImplementedError):
        Base.task_name()


def test_player_task_name():
    assert Player.task_name() == "player"


def test_provider_and_model_returned_from_settings():
    settings = {"provider": "anthropic", "model": "claude-haiku-4-5"}

    assert Player.provider(settings) == "anthropic"
    assert Player.model(settings) == "claude-haiku-4-5"


def test_provider_missing_raises():
    with pytest.raises(ValueError, match="tasks.player.provider is required"):
        Player.provider({})


def test_model_missing_raises():
    with pytest.raises(ValueError, match="tasks.player.model is required"):
        Player.model({})


def test_prompt_override_defaults_false():
    assert Player.prompt_override({}) is False


def test_prompt_override_false_when_not_boolean_true():
    settings = {"prompt_override": {"system": "yes"}}

    assert Player.prompt_override(settings, "system") is False


def test_prompt_override_true():
    settings = {"prompt_override": {"system": True}}

    assert Player.prompt_override(settings, "system") is True


def test_system_prompt_falls_back_to_default_when_no_override(tmp_path):
    default_dir = tmp_path / "default"
    default_dir.mkdir()
    (default_dir / "system.md").write_text("default prompt\n")

    settings = {}

    assert Player.system_prompt(settings, default_prompts_dir=default_dir) == "default prompt"


def test_system_prompt_uses_user_override_when_enabled_and_present(tmp_path):
    default_dir = tmp_path / "default"
    default_dir.mkdir()
    (default_dir / "system.md").write_text("default prompt\n")

    user_dir = tmp_path / "user"
    (user_dir / "player").mkdir(parents=True)
    (user_dir / "player" / "system.md").write_text("custom prompt\n")

    settings = {"prompt_override": {"system": True}}

    result = Player.system_prompt(settings, user_prompts_dir=user_dir, default_prompts_dir=default_dir)

    assert result == "custom prompt"


def test_system_prompt_falls_back_to_default_when_override_enabled_but_user_file_missing(tmp_path):
    default_dir = tmp_path / "default"
    default_dir.mkdir()
    (default_dir / "system.md").write_text("default prompt\n")

    user_dir = tmp_path / "user"
    user_dir.mkdir()

    settings = {"prompt_override": {"system": True}}

    result = Player.system_prompt(settings, user_prompts_dir=user_dir, default_prompts_dir=default_dir)

    assert result == "default prompt"


def test_system_prompt_none_when_no_dirs_given():
    assert Player.system_prompt({}) is None
