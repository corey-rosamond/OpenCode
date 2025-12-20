"""Tests for configuration loader."""

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from watchdog.observers.api import BaseObserver

from code_forge.config.loader import ConfigLoader
from code_forge.config.models import CodeForgeConfig
from code_forge.core import ConfigError


class TestConfigLoaderInit:
    """Tests for ConfigLoader initialization."""

    def test_default_directories(self) -> None:
        """Test default directory paths."""
        loader = ConfigLoader()
        assert loader.user_dir == Path.home() / ".forge"
        assert loader.project_dir == Path.cwd() / ".forge"

    def test_custom_directories(self, tmp_path: Path) -> None:
        """Test custom directory paths."""
        user_dir = tmp_path / "user"
        project_dir = tmp_path / "project"

        loader = ConfigLoader(user_dir=user_dir, project_dir=project_dir)
        assert loader.user_dir == user_dir
        assert loader.project_dir == project_dir


class TestConfigLoaderLoadAll:
    """Tests for ConfigLoader.load_all()."""

    def test_load_defaults_only(self, tmp_path: Path) -> None:
        """Test loading with no config files returns defaults."""
        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=tmp_path / "project",
        )
        config = loader.load_all()

        assert config.model.default == "anthropic/claude-3.5-sonnet"
        assert config.display.theme == "dark"

    def test_load_user_json(self, tmp_path: Path) -> None:
        """Test loading user JSON configuration."""
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "settings.json").write_text(
            '{"model": {"default": "user-model"}}'
        )

        loader = ConfigLoader(
            user_dir=user_dir,
            project_dir=tmp_path / "project",
        )
        config = loader.load_all()

        assert config.model.default == "user-model"

    def test_load_user_yaml(self, tmp_path: Path) -> None:
        """Test loading user YAML configuration."""
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "settings.yaml").write_text("model:\n  default: yaml-model")

        loader = ConfigLoader(
            user_dir=user_dir,
            project_dir=tmp_path / "project",
        )
        config = loader.load_all()

        assert config.model.default == "yaml-model"

    def test_user_json_preferred_over_yaml(self, tmp_path: Path) -> None:
        """Test JSON takes precedence over YAML in user dir."""
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "settings.json").write_text(
            '{"model": {"default": "json-model"}}'
        )
        (user_dir / "settings.yaml").write_text("model:\n  default: yaml-model")

        loader = ConfigLoader(
            user_dir=user_dir,
            project_dir=tmp_path / "project",
        )
        config = loader.load_all()

        assert config.model.default == "json-model"

    def test_load_project_json(self, tmp_path: Path) -> None:
        """Test loading project JSON configuration."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "settings.json").write_text(
            '{"model": {"default": "project-model"}}'
        )

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )
        config = loader.load_all()

        assert config.model.default == "project-model"

    def test_project_overrides_user(self, tmp_path: Path) -> None:
        """Test project config overrides user config."""
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "settings.json").write_text(
            '{"model": {"default": "user-model", "max_tokens": 4096}}'
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "settings.json").write_text(
            '{"model": {"default": "project-model"}}'
        )

        loader = ConfigLoader(user_dir=user_dir, project_dir=project_dir)
        config = loader.load_all()

        # Project overrides user
        assert config.model.default == "project-model"
        # User value preserved where not overridden
        assert config.model.max_tokens == 4096

    def test_load_local_overrides(self, tmp_path: Path) -> None:
        """Test local overrides take precedence."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "settings.json").write_text(
            '{"model": {"default": "project-model"}}'
        )
        (project_dir / "settings.local.json").write_text(
            '{"model": {"default": "local-model"}}'
        )

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )
        config = loader.load_all()

        assert config.model.default == "local-model"

    def test_invalid_config_continues(self, tmp_path: Path) -> None:
        """Test invalid user config doesn't break loading."""
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "settings.json").write_text('{"broken": }')  # Invalid JSON

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "settings.json").write_text(
            '{"model": {"default": "project-model"}}'
        )

        loader = ConfigLoader(user_dir=user_dir, project_dir=project_dir)
        config = loader.load_all()

        # Should still work with project config
        assert config.model.default == "project-model"


class TestConfigLoaderMerge:
    """Tests for ConfigLoader.merge()."""

    def test_merge_simple(self) -> None:
        """Test simple merge."""
        loader = ConfigLoader()
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = loader.merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested(self) -> None:
        """Test nested merge."""
        loader = ConfigLoader()
        base = {"model": {"default": "a", "max_tokens": 100}}
        override = {"model": {"default": "b"}}

        result = loader.merge(base, override)

        assert result["model"]["default"] == "b"
        assert result["model"]["max_tokens"] == 100

    def test_merge_deep_nested(self) -> None:
        """Test deeply nested merge."""
        loader = ConfigLoader()
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 10}}}

        result = loader.merge(base, override)

        assert result["a"]["b"]["c"] == 10
        assert result["a"]["b"]["d"] == 2

    def test_merge_replaces_non_dict(self) -> None:
        """Test non-dict values are replaced."""
        loader = ConfigLoader()
        base = {"a": {"b": 1}}
        override = {"a": "replaced"}

        result = loader.merge(base, override)

        assert result["a"] == "replaced"

    def test_merge_preserves_base(self) -> None:
        """Test merge doesn't modify base."""
        loader = ConfigLoader()
        base = {"a": 1}
        override = {"b": 2}

        loader.merge(base, override)

        assert base == {"a": 1}  # Unchanged


class TestConfigLoaderLoad:
    """Tests for ConfigLoader.load()."""

    def test_load_json(self, tmp_path: Path) -> None:
        """Test loading single JSON file."""
        config_file = tmp_path / "test.json"
        config_file.write_text('{"model": {"default": "test"}}')

        loader = ConfigLoader()
        data = loader.load(config_file)

        assert data["model"]["default"] == "test"

    def test_load_yaml(self, tmp_path: Path) -> None:
        """Test loading single YAML file."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("model:\n  default: test")

        loader = ConfigLoader()
        data = loader.load(config_file)

        assert data["model"]["default"] == "test"

    def test_load_yml(self, tmp_path: Path) -> None:
        """Test loading single .yml file."""
        config_file = tmp_path / "test.yml"
        config_file.write_text("model:\n  default: test")

        loader = ConfigLoader()
        data = loader.load(config_file)

        assert data["model"]["default"] == "test"

    def test_load_unsupported_format(self, tmp_path: Path) -> None:
        """Test loading unsupported format raises error."""
        config_file = tmp_path / "test.toml"
        config_file.write_text("[model]\ndefault = 'test'")

        loader = ConfigLoader()
        with pytest.raises(ConfigError) as exc_info:
            loader.load(config_file)

        assert "Unsupported" in str(exc_info.value)


class TestConfigLoaderValidate:
    """Tests for ConfigLoader.validate()."""

    def test_validate_valid_config(self) -> None:
        """Test validating valid configuration."""
        loader = ConfigLoader()
        config = {"model": {"default": "gpt-5", "max_tokens": 8192}}

        is_valid, errors = loader.validate(config)

        assert is_valid is True
        assert errors == []

    def test_validate_invalid_config(self) -> None:
        """Test validating invalid configuration."""
        loader = ConfigLoader()
        config = {"model": {"max_tokens": 500000}}  # Over max

        is_valid, errors = loader.validate(config)

        assert is_valid is False
        assert len(errors) > 0


class TestConfigLoaderProperty:
    """Tests for ConfigLoader.config property."""

    def test_config_cached(self, tmp_path: Path) -> None:
        """Test config property caches result."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "settings.json").write_text(
            '{"model": {"default": "cached-model"}}'
        )

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )

        config1 = loader.config
        config2 = loader.config

        assert config1 is config2  # Same object
        assert config1.model.default == "cached-model"


class TestConfigLoaderReload:
    """Tests for ConfigLoader.reload()."""

    def test_reload_updates_config(self, tmp_path: Path) -> None:
        """Test reload updates cached config."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_file = project_dir / "settings.json"
        config_file.write_text('{"model": {"default": "original"}}')

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )

        # Load initial config
        config1 = loader.config
        assert config1.model.default == "original"

        # Update file
        config_file.write_text('{"model": {"default": "updated"}}')

        # Reload
        loader.reload()

        config2 = loader.config
        assert config2.model.default == "updated"

    def test_reload_invalid_keeps_old(self, tmp_path: Path) -> None:
        """Test reload with invalid config keeps old config."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_file = project_dir / "settings.json"
        config_file.write_text('{"model": {"default": "original"}}')

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )

        # Load initial config
        config1 = loader.config
        assert config1.model.default == "original"

        # Write invalid config
        config_file.write_text('{"model": {"max_tokens": 999999999}}')

        # Reload should fail but keep old config
        loader.reload()

        config2 = loader.config
        # Should still have old config (max_tokens validation should fail)
        assert config2.model.default == "original"


class TestConfigLoaderObservers:
    """Tests for ConfigLoader observer pattern."""

    def test_add_observer(self, tmp_path: Path) -> None:
        """Test adding observer."""
        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=tmp_path / "project",
        )

        callback = MagicMock()
        loader.add_observer(callback)

        # Force a reload to trigger observers
        loader.reload()

        callback.assert_called_once()
        assert isinstance(callback.call_args[0][0], CodeForgeConfig)

    def test_add_observer_not_duplicated(self, tmp_path: Path) -> None:
        """Test same observer is not added twice."""
        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=tmp_path / "project",
        )

        callback = MagicMock()
        loader.add_observer(callback)
        loader.add_observer(callback)

        loader.reload()

        callback.assert_called_once()

    def test_remove_observer(self, tmp_path: Path) -> None:
        """Test removing observer."""
        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=tmp_path / "project",
        )

        callback = MagicMock()
        loader.add_observer(callback)
        loader.remove_observer(callback)

        loader.reload()

        callback.assert_not_called()

    def test_observer_exception_handled(self, tmp_path: Path) -> None:
        """Test observer exceptions don't break reload."""
        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=tmp_path / "project",
        )

        bad_callback = MagicMock(side_effect=Exception("Observer error"))
        good_callback = MagicMock()

        loader.add_observer(bad_callback)
        loader.add_observer(good_callback)

        # Should not raise
        loader.reload()

        # Both should be called despite exception
        bad_callback.assert_called_once()
        good_callback.assert_called_once()


class TestConfigLoaderWatch:
    """Tests for ConfigLoader file watching."""

    def test_watch_starts_watcher(self, tmp_path: Path) -> None:
        """Test watch() starts file watcher."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )

        try:
            loader.watch()
            assert isinstance(loader._file_watcher, BaseObserver)
        finally:
            loader.stop_watching()

    def test_watch_idempotent(self, tmp_path: Path) -> None:
        """Test calling watch() multiple times is safe."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )

        try:
            loader.watch()
            watcher1 = loader._file_watcher
            loader.watch()
            watcher2 = loader._file_watcher
            assert watcher1 is watcher2
        finally:
            loader.stop_watching()

    def test_stop_watching(self, tmp_path: Path) -> None:
        """Test stop_watching() stops watcher."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )

        loader.watch()
        loader.stop_watching()

        assert loader._file_watcher is None

    def test_stop_watching_idempotent(self, tmp_path: Path) -> None:
        """Test calling stop_watching() multiple times is safe."""
        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=tmp_path / "project",
        )

        # Should not raise even if never started
        loader.stop_watching()
        loader.stop_watching()


class TestConfigLoaderEnvironment:
    """Tests for environment variable integration."""

    def test_env_overrides_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test environment variables override file config."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "settings.json").write_text(
            '{"model": {"default": "file-model"}}'
        )

        monkeypatch.setenv("FORGE_MODEL", "env-model")

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=project_dir,
        )
        config = loader.load_all()

        assert config.model.default == "env-model"

    def test_env_api_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API key from environment."""
        monkeypatch.setenv("FORGE_API_KEY", "sk-secret-123")

        loader = ConfigLoader(
            user_dir=tmp_path / "user",
            project_dir=tmp_path / "project",
        )
        config = loader.load_all()

        assert config.get_api_key() == "sk-secret-123"


class TestConfigLoaderHierarchy:
    """Tests for full configuration hierarchy."""

    def test_full_hierarchy(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete hierarchy precedence."""
        # Setup directories
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # User config
        (user_dir / "settings.json").write_text(json.dumps({
            "model": {"default": "user-model", "max_tokens": 1000},
            "display": {"theme": "light", "show_tokens": False},
        }))

        # Project config
        (project_dir / "settings.json").write_text(json.dumps({
            "model": {"default": "project-model"},
            "display": {"theme": "dark"},
        }))

        # Local override
        (project_dir / "settings.local.json").write_text(json.dumps({
            "model": {"default": "local-model"},
        }))

        # Environment
        monkeypatch.setenv("FORGE_MODEL", "env-model")

        loader = ConfigLoader(user_dir=user_dir, project_dir=project_dir)
        config = loader.load_all()

        # Environment has highest precedence
        assert config.model.default == "env-model"
        # User value preserved (not overridden by project or local)
        assert config.model.max_tokens == 1000
        # Project overrides user
        assert config.display.theme == "dark"
        # User value preserved where not overridden
        assert config.display.show_tokens is False
