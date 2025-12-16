"""Plugin discovery from various sources."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

from .exceptions import PluginManifestError
from .manifest import ManifestParser, PluginManifest

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredPlugin:
    """Discovered plugin information.

    Contains the manifest and source information for a discovered plugin
    before it has been loaded.

    Attributes:
        path: Path to plugin directory (None for package plugins).
        manifest: Parsed plugin manifest.
        source: Discovery source ("user", "project", "package", "extra").
    """

    path: Path | None
    manifest: PluginManifest
    source: str  # "user", "project", "package", "extra"

    @property
    def id(self) -> str:
        """Get plugin ID.

        Returns:
            The plugin's unique identifier (name from manifest).
        """
        return self.manifest.name


class PluginDiscovery:
    """Discover plugins from various sources.

    Searches for plugins in:
    - User plugin directory (~/.forge/plugins/)
    - Project plugin directory (.forge/plugins/)
    - Installed Python packages (via entry points)
    - Additional configured paths

    SECURITY WARNING:
        Plugin discovery executes code from installed packages when loading
        entry points. Only install plugins from trusted sources. A malicious
        package could execute arbitrary code during the discovery process.

        Future improvements may include:
        - Plugin signing and verification
        - Sandboxed plugin execution
        - Plugin allowlist/blocklist configuration

    Attributes:
        USER_PLUGIN_DIR: Default user plugin directory.
        PROJECT_PLUGIN_DIR: Default project plugin directory.
        ENTRY_POINT_GROUP: Entry point group name for package plugins.
    """

    USER_PLUGIN_DIR = Path.home() / ".forge" / "plugins"
    PROJECT_PLUGIN_DIR = Path(".forge") / "plugins"
    ENTRY_POINT_GROUP = "code_forge.plugins"

    def __init__(
        self,
        user_dir: Path | None = None,
        project_dir: Path | None = None,
        extra_paths: list[Path] | None = None,
    ) -> None:
        """Initialize plugin discovery.

        Args:
            user_dir: User plugin directory. Default ~/.forge/plugins
            project_dir: Project plugin directory. Default .forge/plugins
            extra_paths: Additional paths to search.
        """
        self.user_dir = user_dir or self.USER_PLUGIN_DIR
        self.project_dir = project_dir or self.PROJECT_PLUGIN_DIR
        self.extra_paths = extra_paths or []
        self.parser = ManifestParser()

    def discover(self) -> list[DiscoveredPlugin]:
        """Discover all plugins from all sources.

        Searches user directory, project directory, extra paths,
        and installed Python packages.

        Returns:
            List of all discovered plugins.
        """
        plugins: list[DiscoveredPlugin] = []

        # Discover from directories
        plugins.extend(self.discover_user_plugins())
        plugins.extend(self.discover_project_plugins())
        plugins.extend(self.discover_extra_plugins())

        # Discover from installed packages
        plugins.extend(self.discover_package_plugins())

        return plugins

    def discover_user_plugins(self) -> list[DiscoveredPlugin]:
        """Discover plugins in user directory.

        Returns:
            List of plugins found in user directory.
        """
        return list(self._discover_from_dir(self.user_dir, "user"))

    def discover_project_plugins(self) -> list[DiscoveredPlugin]:
        """Discover plugins in project directory.

        Returns:
            List of plugins found in project directory.
        """
        return list(self._discover_from_dir(self.project_dir, "project"))

    def discover_extra_plugins(self) -> list[DiscoveredPlugin]:
        """Discover plugins from extra paths.

        Returns:
            List of plugins found in extra paths.
        """
        plugins: list[DiscoveredPlugin] = []
        for path in self.extra_paths:
            plugins.extend(self._discover_from_dir(path, "extra"))
        return plugins

    def discover_package_plugins(self) -> list[DiscoveredPlugin]:
        """Discover plugins from installed packages.

        Searches for Python packages that have registered
        code_forge.plugins entry points.

        SECURITY WARNING: Loading entry points executes code from installed
        packages. Only install plugins from trusted sources. A malicious
        package could execute arbitrary code during discovery. In the future,
        consider implementing plugin signing/verification.

        Returns:
            List of plugins found via entry points.
        """
        plugins: list[DiscoveredPlugin] = []

        try:
            eps = entry_points(group=self.ENTRY_POINT_GROUP)
        except TypeError:
            # Python 3.9 compatibility - entry_points() returns a dict
            all_eps = entry_points()
            eps = getattr(all_eps, "get", lambda _k, d: d)(self.ENTRY_POINT_GROUP, [])

        for ep in eps:
            try:
                # SECURITY: ep.load() executes code from the package.
                # This is inherent to Python's entry point system.
                # Only install packages from trusted sources.
                logger.debug(
                    f"Loading plugin entry point: {ep.name} from {ep.value} "
                    "(SECURITY: executes package code)"
                )
                plugin_class = ep.load()

                # Create a manifest from the plugin class
                if hasattr(plugin_class, "metadata"):
                    instance = plugin_class()
                    meta = instance.metadata
                    caps = instance.capabilities

                    manifest = PluginManifest(
                        name=meta.name,
                        version=meta.version,
                        description=meta.description,
                        entry_point=f"{ep.value}",
                        metadata=meta,
                        capabilities=caps,
                    )

                    plugins.append(
                        DiscoveredPlugin(
                            path=None,
                            manifest=manifest,
                            source="package",
                        )
                    )

            except Exception as e:
                # Log but continue
                logger.warning(f"Failed to load plugin entry point {ep.name}: {e}")

        return plugins

    def _discover_from_dir(
        self, directory: Path, source: str
    ) -> Iterator[DiscoveredPlugin]:
        """Discover plugins from a directory.

        Scans directory for subdirectories containing plugin manifests.

        Args:
            directory: Directory to scan.
            source: Source identifier for discovered plugins.

        Yields:
            DiscoveredPlugin for each valid plugin found.
        """
        if not directory.exists():
            return

        for item in directory.iterdir():
            if not item.is_dir():
                continue

            manifest_path = self.parser.find_manifest(item)
            if manifest_path is None:
                continue

            try:
                manifest = self.parser.parse(manifest_path)

                # Validate manifest
                errors = self.parser.validate(manifest)
                if errors:
                    logger.warning(f"Invalid manifest in {item}: {errors}")
                    continue

                yield DiscoveredPlugin(
                    path=item,
                    manifest=manifest,
                    source=source,
                )

            except PluginManifestError as e:
                logger.warning(f"Failed to parse manifest in {item}: {e}")
