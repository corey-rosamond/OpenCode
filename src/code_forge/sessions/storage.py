"""Session persistence layer."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Session

logger = logging.getLogger(__name__)


class SessionStorageError(Exception):
    """Error during session storage operations."""

    pass


class SessionNotFoundError(SessionStorageError):
    """Session not found in storage."""

    pass


class SessionCorruptedError(SessionStorageError):
    """Session file is corrupted."""

    pass


class SessionStorage:
    """Handles session persistence to disk.

    Sessions are stored as JSON files in a configurable directory.
    Supports atomic writes and backup before overwrite.
    Includes automatic backup rotation to prevent unbounded disk usage.

    Attributes:
        storage_dir: Directory where sessions are stored.
    """

    DEFAULT_DIR_NAME = "sessions"
    SESSION_EXTENSION = ".json"
    BACKUP_EXTENSION = ".backup"
    MAX_BACKUPS = 100  # Maximum number of backup files to keep
    BACKUP_MAX_AGE_DAYS = 7  # Maximum age of backup files in days

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        """Initialize session storage.

        Args:
            storage_dir: Directory for session files. Uses default if None.
        """
        if storage_dir is None:
            storage_dir = self.get_default_dir()
        elif isinstance(storage_dir, str):
            storage_dir = Path(storage_dir)

        self.storage_dir = storage_dir
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # Set secure permissions (owner only)
        with contextlib.suppress(OSError):
            self.storage_dir.chmod(0o700)

    @classmethod
    def get_default_dir(cls) -> Path:
        """Get the default session storage directory.

        Returns:
            Path to default storage directory.
        """
        # Use XDG_DATA_HOME if available, else ~/.local/share
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"

        return base / "forge" / cls.DEFAULT_DIR_NAME

    @classmethod
    def get_project_dir(cls, project_root: Path | str) -> Path:
        """Get the project-local session storage directory.

        Args:
            project_root: Root directory of the project.

        Returns:
            Path to project session directory.
        """
        if isinstance(project_root, str):
            project_root = Path(project_root)
        return project_root / ".forge" / cls.DEFAULT_DIR_NAME

    def get_path(self, session_id: str) -> Path:
        """Get the file path for a session.

        Args:
            session_id: The session ID.

        Returns:
            Path to the session file.
        """
        return self.storage_dir / f"{session_id}{self.SESSION_EXTENSION}"

    def get_backup_path(self, session_id: str) -> Path:
        """Get the backup file path for a session.

        Args:
            session_id: The session ID.

        Returns:
            Path to the backup file.
        """
        return self.storage_dir / f"{session_id}{self.BACKUP_EXTENSION}"

    def exists(self, session_id: str) -> bool:
        """Check if a session exists in storage.

        Args:
            session_id: The session ID to check.

        Returns:
            True if the session exists.
        """
        return self.get_path(session_id).exists()

    def save(self, session: Session) -> None:
        """Save a session to storage.

        Uses atomic write (write to temp file, then rename) for safety.
        Creates a backup of the existing file before overwrite.

        Args:
            session: The session to save.

        Raises:
            SessionStorageError: If save fails.
        """
        session_path = self.get_path(session.id)
        backup_path = self.get_backup_path(session.id)

        # Create backup if file exists
        if session_path.exists():
            try:
                shutil.copy2(session_path, backup_path)
            except OSError as e:
                logger.warning(f"Failed to create backup: {e}")

        # Serialize session
        try:
            json_data = session.to_json()
        except Exception as e:
            raise SessionStorageError(f"Failed to serialize session: {e}") from e

        # Atomic write: write to temp file, then rename
        try:
            fd, temp_path = tempfile.mkstemp(
                suffix=self.SESSION_EXTENSION,
                dir=self.storage_dir,
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(json_data)

                # Rename temp file to target (atomic on POSIX)
                Path(temp_path).replace(session_path)

                # Set secure permissions
                with contextlib.suppress(OSError):
                    session_path.chmod(0o600)

            except Exception:
                # Clean up temp file on failure
                with contextlib.suppress(OSError):
                    Path(temp_path).unlink()
                raise

        except OSError as e:
            raise SessionStorageError(f"Failed to save session: {e}") from e

        logger.debug(f"Saved session {session.id}")

    def load(self, session_id: str, auto_recover: bool = True) -> Session:
        """Load a session from storage.

        Args:
            session_id: The session ID to load.
            auto_recover: If True, attempt recovery from backup on corruption.

        Returns:
            The loaded Session.

        Raises:
            SessionNotFoundError: If session doesn't exist.
            SessionCorruptedError: If session file is corrupted and recovery failed.
        """
        from .models import Session

        session_path = self.get_path(session_id)

        if not session_path.exists():
            raise SessionNotFoundError(f"Session not found: {session_id}")

        try:
            with session_path.open(encoding="utf-8") as f:
                json_data = f.read()

            session = Session.from_json(json_data)
            logger.debug(f"Loaded session {session_id}")
            return session

        except json.JSONDecodeError as e:
            # Attempt automatic recovery from backup
            if auto_recover and self.recover_from_backup(session_id):
                logger.warning(
                    f"Session {session_id} was corrupted, recovered from backup"
                )
                # Retry load after recovery (with auto_recover=False to prevent loops)
                return self.load(session_id, auto_recover=False)

            raise SessionCorruptedError(
                f"Session file corrupted: {session_id}. "
                f"Backup recovery {'failed' if auto_recover else 'disabled'}."
            ) from e
        except Exception as e:
            raise SessionStorageError(f"Failed to load session: {e}") from e

    def load_or_none(self, session_id: str) -> Session | None:
        """Load a session, returning None if not found or corrupted.

        Args:
            session_id: The session ID to load.

        Returns:
            The loaded Session, or None if unavailable.
        """
        try:
            return self.load(session_id)
        except SessionStorageError as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
            return None

    def delete(self, session_id: str) -> bool:
        """Delete a session from storage.

        Also removes any backup file.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if session was deleted, False if it didn't exist.
        """
        session_path = self.get_path(session_id)
        backup_path = self.get_backup_path(session_id)

        deleted = False

        if session_path.exists():
            try:
                session_path.unlink()
                deleted = True
                logger.debug(f"Deleted session {session_id}")
            except OSError as e:
                logger.error(f"Failed to delete session: {e}")

        if backup_path.exists():
            with contextlib.suppress(OSError):
                backup_path.unlink()

        return deleted

    def list_session_ids(self) -> list[str]:
        """List all session IDs in storage.

        Returns:
            List of session IDs.
        """
        session_ids = []

        for path in self.storage_dir.glob(f"*{self.SESSION_EXTENSION}"):
            session_id = path.stem
            # Skip the index file (index.json -> stem is "index")
            if session_id == "index":
                continue
            session_ids.append(session_id)

        return session_ids

    def recover_from_backup(self, session_id: str) -> bool:
        """Recover a session from its backup file.

        Args:
            session_id: The session ID to recover.

        Returns:
            True if recovery succeeded.
        """
        session_path = self.get_path(session_id)
        backup_path = self.get_backup_path(session_id)

        if not backup_path.exists():
            return False

        try:
            shutil.copy2(backup_path, session_path)
            logger.info(f"Recovered session {session_id} from backup")
            return True
        except OSError as e:
            logger.error(f"Failed to recover session: {e}")
            return False

    def get_storage_size(self) -> int:
        """Get total size of all session files in bytes.

        Returns:
            Total size in bytes.
        """
        total = 0
        for path in self.storage_dir.glob(f"*{self.SESSION_EXTENSION}"):
            with contextlib.suppress(OSError):
                total += path.stat().st_size
        return total

    def cleanup_old_sessions(
        self,
        max_age_days: int = 30,
        keep_minimum: int = 10,
    ) -> list[str]:
        """Delete sessions older than a certain age.

        Args:
            max_age_days: Maximum age in days.
            keep_minimum: Minimum number of sessions to keep.

        Returns:
            List of deleted session IDs.
        """

        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

        # Load all sessions with their dates
        sessions_with_dates: list[tuple[str, datetime]] = []

        for session_id in self.list_session_ids():
            session = self.load_or_none(session_id)
            if session:
                sessions_with_dates.append((session_id, session.updated_at))

        # Sort by date (newest first)
        sessions_with_dates.sort(key=lambda x: x[1], reverse=True)

        # Delete old sessions, keeping minimum
        deleted = []
        for i, (session_id, updated_at) in enumerate(sessions_with_dates):
            if i < keep_minimum:
                continue  # Keep minimum sessions

            if updated_at < cutoff and self.delete(session_id):
                deleted.append(session_id)

        if deleted:
            logger.info(f"Cleaned up {len(deleted)} old sessions")

        return deleted

    def cleanup_old_backups(self) -> int:
        """Remove old backup files to prevent unbounded disk usage.

        Removes backups that:
        - Are older than BACKUP_MAX_AGE_DAYS
        - Exceed MAX_BACKUPS count (oldest first)

        Returns:
            Number of backup files deleted.
        """
        deleted_count = 0
        cutoff_time = time.time() - (self.BACKUP_MAX_AGE_DAYS * 24 * 3600)

        # Get all backup files with modification times
        backups: list[tuple[Path, float]] = []
        for path in self.storage_dir.glob(f"*{self.BACKUP_EXTENSION}"):
            try:
                mtime = path.stat().st_mtime
                backups.append((path, mtime))
            except OSError:
                continue

        # Sort by modification time (oldest first)
        backups.sort(key=lambda x: x[1])

        # Delete old backups (by age)
        for path, mtime in backups:
            if mtime < cutoff_time:
                try:
                    path.unlink()
                    deleted_count += 1
                except OSError:
                    pass

        # Re-fetch remaining backups
        remaining = [(p, m) for p, m in backups if p.exists()]

        # Delete excess backups (by count, oldest first)
        excess_count = len(remaining) - self.MAX_BACKUPS
        if excess_count > 0:
            for path, _ in remaining[:excess_count]:
                try:
                    path.unlink()
                    deleted_count += 1
                except OSError:
                    pass

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backup files")

        return deleted_count
