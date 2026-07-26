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
    with pytest.raises(ValueError, match=r"tasks\.player\.provider is required in settings\.yaml"):
        Player.provider({})


def test_model_missing_raises():
    with pytest.raises(ValueError, match=r"tasks\.player\.model is required in settings\.yaml"):
        Player.model({})


def test_provider_raises_for_non_dict_settings():
    # Deliberately passing a non-dict value to exercise the runtime guard against malformed
    # settings (e.g. from hand-edited YAML) — intentionally violates the declared param type.
    with pytest.raises(ValueError, match="required in settings.yaml"):
        Player.provider("not a dict")  # ty: ignore[invalid-argument-type]


def test_model_raises_for_non_dict_settings():
    with pytest.raises(ValueError, match="required in settings.yaml"):
        Player.model("not a dict")  # ty: ignore[invalid-argument-type]


def test_prompt_override_false_for_non_dict_settings():
    assert Player.prompt_override("not a dict") is False  # ty: ignore[invalid-argument-type]
    assert Player.prompt_override(None) is False
    assert Player.prompt_override([1, 2, 3]) is False  # ty: ignore[invalid-argument-type]


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


def test_max_iterations_defaults_to_25():
    assert Player.max_iterations({}) == 25


def test_max_iterations_reads_from_settings():
    assert Player.max_iterations({"max_iterations": 10}) == 10


def test_max_output_tokens_defaults_to_1024():
    assert Player.max_output_tokens({}) == 1024


def test_max_output_tokens_reads_from_settings():
    assert Player.max_output_tokens({"max_output_tokens": 2048}) == 2048


def test_max_iterations_coerces_string_setting_to_int():
    assert Player.max_iterations({"max_iterations": "5"}) == 5


def test_max_iterations_tolerates_non_dict_settings():
    assert Player.max_iterations("not a dict") == 25  # ty: ignore[invalid-argument-type]
