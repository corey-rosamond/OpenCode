"""Permission configuration management."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from code_forge.permissions.models import PermissionLevel, PermissionRule
from code_forge.permissions.rules import RuleSet

logger = logging.getLogger(__name__)


# Default permission rules
DEFAULT_RULES: list[PermissionRule] = [
    # Allow read operations
    PermissionRule(
        pattern="tool:read",
        permission=PermissionLevel.ALLOW,
        description="Allow file reading",
    ),
    PermissionRule(
        pattern="tool:glob",
        permission=PermissionLevel.ALLOW,
        description="Allow file searching",
    ),
    PermissionRule(
        pattern="tool:grep",
        permission=PermissionLevel.ALLOW,
        description="Allow content searching",
    ),
    PermissionRule(
        pattern="tool:bash_output",
        permission=PermissionLevel.ALLOW,
        description="Allow reading shell output",
    ),
    # Ask for write operations
    PermissionRule(
        pattern="tool:write",
        permission=PermissionLevel.ASK,
        description="Confirm file writing",
    ),
    PermissionRule(
        pattern="tool:edit",
        permission=PermissionLevel.ASK,
        description="Confirm file editing",
    ),
    PermissionRule(
        pattern="tool:notebook_edit",
        permission=PermissionLevel.ASK,
        description="Confirm notebook editing",
    ),
    # Ask for execution
    PermissionRule(
        pattern="tool:bash",
        permission=PermissionLevel.ASK,
        description="Confirm shell commands",
    ),
    PermissionRule(
        pattern="tool:kill_shell",
        permission=PermissionLevel.ASK,
        description="Confirm killing shell",
    ),
    # Deny dangerous patterns
    PermissionRule(
        pattern="tool:bash,arg:command:*rm -rf*",
        permission=PermissionLevel.DENY,
        description="Block recursive force delete",
        priority=50,
    ),
    PermissionRule(
        pattern="tool:bash,arg:command:*rm -fr*",
        permission=PermissionLevel.DENY,
        description="Block recursive force delete",
        priority=50,
    ),
    PermissionRule(
        pattern="tool:bash,arg:command:*> /dev/*",
        permission=PermissionLevel.DENY,
        description="Block writing to devices",
        priority=50,
    ),
    PermissionRule(
        pattern="tool:bash,arg:command:*mkfs*",
        permission=PermissionLevel.DENY,
        description="Block filesystem creation",
        priority=50,
    ),
    PermissionRule(
        pattern="tool:bash,arg:command:*dd if=*",
        permission=PermissionLevel.DENY,
        description="Block dd command",
        priority=50,
    ),
    PermissionRule(
        pattern="tool:write,arg:file_path:/etc/*",
        permission=PermissionLevel.DENY,
        description="Block writing to /etc",
        priority=50,
    ),
    PermissionRule(
        pattern="tool:write,arg:file_path:/usr/*",
        permission=PermissionLevel.DENY,
        description="Block writing to /usr",
        priority=50,
    ),
    PermissionRule(
        pattern="tool:edit,arg:file_path:/etc/*",
        permission=PermissionLevel.DENY,
        description="Block editing /etc files",
        priority=50,
    ),
]


class PermissionConfig:
    """Manages permission configuration files."""

    GLOBAL_FILE = "permissions.json"
    PROJECT_FILE = ".forge/permissions.json"

    @classmethod
    def get_global_path(cls) -> Path:
        """Get path to global permissions file."""
        # Use XDG_CONFIG_HOME or default to ~/.config
        config_home = Path.home() / ".config" / "forge"
        return config_home / cls.GLOBAL_FILE

    @classmethod
    def get_project_path(cls, project_root: Path | None = None) -> Path | None:
        """Get path to project permissions file."""
        if project_root is None:
            return None
        return project_root / cls.PROJECT_FILE

    @classmethod
    def load_global(cls) -> RuleSet:
        """
        Load global permission rules.

        If no global config exists, returns default rules.
        """
        path = cls.get_global_path()

        if path.exists():
            try:
                with path.open(encoding="utf-8") as f:
                    data = json.load(f)
                rules = RuleSet.from_dict(data)
                logger.debug("Loaded %d global permission rules", len(rules))
                return rules
            except json.JSONDecodeError as e:
                logger.warning(
                    "JSON parse error in %s (line %d, column %d): %s",
                    path,
                    e.lineno,
                    e.colno,
                    e.msg,
                )
            except (KeyError, ValueError) as e:
                logger.warning("Error loading global permissions from %s: %s", path, e)

        # Return default rules
        return cls.get_default_rules()

    @classmethod
    def load_project(cls, project_root: Path | None) -> RuleSet | None:
        """
        Load project-specific permission rules.

        Returns None if no project config exists.
        """
        path = cls.get_project_path(project_root)

        if path is None or not path.exists():
            return None

        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            rules = RuleSet.from_dict(data)
            logger.debug("Loaded %d project permission rules", len(rules))
            return rules
        except json.JSONDecodeError as e:
            logger.warning(
                "JSON parse error in %s (line %d, column %d): %s",
                path,
                e.lineno,
                e.colno,
                e.msg,
            )
            return None
        except (KeyError, ValueError) as e:
            logger.warning("Error loading project permissions from %s: %s", path, e)
            return None

    @classmethod
    def save_global(cls, rules: RuleSet) -> None:
        """Save global permission rules."""
        path = cls.get_global_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(rules.to_dict(), f, indent=2)

        logger.debug("Saved %d global permission rules", len(rules))

    @classmethod
    def save_project(cls, project_root: Path, rules: RuleSet) -> None:
        """Save project-specific permission rules."""
        path = project_root / cls.PROJECT_FILE
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(rules.to_dict(), f, indent=2)

        logger.debug("Saved %d project permission rules", len(rules))

    @classmethod
    def get_default_rules(cls) -> RuleSet:
        """Get the default permission rules."""
        return RuleSet(
            rules=list(DEFAULT_RULES),
            default=PermissionLevel.ASK,
        )

    @classmethod
    def reset_to_defaults(cls) -> None:
        """Reset global permissions to defaults."""
        cls.save_global(cls.get_default_rules())
