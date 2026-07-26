from pathlib import Path

import boukensha.config as config_module
from boukensha import Config


def write_settings(boukensha_dir: Path, yaml_text: str) -> None:
    boukensha_dir.mkdir(parents=True, exist_ok=True)
    (boukensha_dir / "settings.yaml").write_text(yaml_text)


def test_resolve_dir_uses_boukensha_dir_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))

    config = Config()

    assert config.dir == tmp_path.resolve()


def test_resolve_dir_falls_back_to_default_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)
    monkeypatch.setattr(config_module, "DEFAULT_DIR", tmp_path / ".boukensha")

    config = Config()

    assert config.dir == (tmp_path / ".boukensha").resolve()


def test_load_settings_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))

    config = Config()

    assert config.settings == {}


def test_load_settings_reads_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))
    write_settings(
        tmp_path,
        """
        tasks:
          player:
            provider: anthropic
            model: claude-haiku-4-5
        mud:
          host: localhost
          port: 4000
        """,
    )

    config = Config()

    assert config.tasks("player") == {"provider": "anthropic", "model": "claude-haiku-4-5"}
    assert list(config.tasks().keys()) == ["player"]


def test_dig_returns_none_for_missing_path(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))

    config = Config()

    assert config.dig("mud", "host") is None
    assert config.dig("nope") is None


def test_dig_short_circuits_through_non_dict_nodes(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))
    write_settings(tmp_path, "mud: not-a-mapping\n")

    config = Config()

    assert config.dig("mud", "host") is None


def test_mud_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))

    config = Config()

    assert config.mud_host == "localhost"
    assert config.mud_port == 4000
    assert config.mud_username is None
    assert config.mud_password is None


def test_mud_values_from_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))
    write_settings(
        tmp_path,
        """
        mud:
          host: mud.example.com
          port: 5000
          username: dummy
          password: helloworld
        """,
    )

    config = Config()

    assert config.mud_host == "mud.example.com"
    assert config.mud_port == 5000
    assert config.mud_username == "dummy"
    assert config.mud_password == "helloworld"


def test_user_prompts_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))

    config = Config()

    assert config.user_prompts_dir == tmp_path.resolve() / "prompts"


def test_str_lists_task_names(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))
    write_settings(tmp_path, "tasks:\n  player:\n    provider: anthropic\n    model: claude-haiku-4-5\n")

    config = Config()

    assert str(config) == f"#<Boukensha::Config dir={config.dir} tasks=player>"
