"""Bash command file modification detector.

This module provides pattern-based detection of files that may be
modified by shell commands, enabling undo support for Bash operations.

Example:
    from code_forge.undo.bash_detector import BashFileDetector

    # Detect files that will be modified
    files = BashFileDetector.detect_files(
        "echo 'hello' > output.txt && rm old.txt",
        working_dir="/project"
    )
    # Returns: ['/project/output.txt', '/project/old.txt']
"""

from __future__ import annotations

import os
import re
from typing import ClassVar


class BashFileDetector:
    """Detect files that a bash command may modify.

    Uses regex patterns to identify common file-modifying operations
    in shell commands. This is inherently imperfect but catches the
    most common cases.

    Limitations:
        - Cannot detect files modified by scripts/programs
        - Cannot expand shell variables or globs
        - May produce false positives for complex commands
        - Cannot detect files modified by subshells
    """

    # Patterns for file-modifying commands
    # Each tuple: (pattern, group_number_for_file_path)
    WRITE_PATTERNS: ClassVar[list[tuple[str, int]]] = [
        # Output redirection: > file, >> file
        (r">\s*([^\s|&;><]+)", 1),
        (r">>\s*([^\s|&;><]+)", 1),

        # rm command: rm file, rm -rf dir
        (r"\brm\s+(?:-[rfiv]*\s+)*([^\s|&;><]+)", 1),

        # mv command (destination): mv src dest
        (r"\bmv\s+(?:-[fivn]*\s+)*\S+\s+([^\s|&;><]+)", 1),

        # cp command (destination): cp src dest
        (r"\bcp\s+(?:-[rfpai]*\s+)*\S+\s+([^\s|&;><]+)", 1),

        # touch command: touch file
        (r"\btouch\s+(?:-[acdmt]*\s+)*([^\s|&;><]+)", 1),

        # mkdir command: mkdir dir
        (r"\bmkdir\s+(?:-[pm]*\s+)*([^\s|&;><]+)", 1),

        # rmdir command: rmdir dir
        (r"\brmdir\s+(?:-[p]*\s+)*([^\s|&;><]+)", 1),

        # sed in-place: sed -i 's/foo/bar/' file
        (r"\bsed\s+-i[^\s]*\s+['\"][^'\"]*['\"]\s+([^\s|&;><]+)", 1),
        (r"\bsed\s+--in-place[^\s]*\s+['\"][^'\"]*['\"]\s+([^\s|&;><]+)", 1),

        # chmod/chown: chmod 755 file
        (r"\bchmod\s+(?:-[R]*\s+)*\S+\s+([^\s|&;><]+)", 1),
        (r"\bchown\s+(?:-[R]*\s+)*\S+(?::\S*)?\s+([^\s|&;><]+)", 1),

        # truncate: truncate -s 0 file
        (r"\btruncate\s+(?:-s\s+\d+\s+)?([^\s|&;><]+)", 1),

        # dd output: dd if=... of=file
        (r"\bdd\s+[^|&;]*\bof=([^\s|&;><]+)", 1),

        # tee: command | tee file
        (r"\btee\s+(?:-a\s+)?([^\s|&;><]+)", 1),

        # cat with heredoc redirect: cat > file << EOF
        (r"\bcat\s*>\s*([^\s|&;><]+)", 1),

        # echo/printf redirect: echo "text" > file
        (r"\b(?:echo|printf)\s+[^|&;]*>\s*([^\s|&;><]+)", 1),
    ]

    # Patterns that indicate we shouldn't try to detect (too complex)
    SKIP_PATTERNS: ClassVar[list[str]] = [
        r"\$\(",      # Command substitution
        r"`[^`]+`",   # Backtick substitution
        r"\*",        # Glob wildcards
        r"\?",        # Single char wildcards
        r"\[.*\]",    # Character classes
        r"\$\{",      # Variable expansion with braces
    ]

    @classmethod
    def detect_files(cls, command: str, working_dir: str) -> list[str]:
        """Extract file paths from a command.

        Args:
            command: Shell command to analyze.
            working_dir: Working directory for relative paths.

        Returns:
            List of absolute paths that may be modified.
        """
        files: list[str] = []

        # Skip complex commands we can't reliably parse
        for skip_pattern in cls.SKIP_PATTERNS:
            if re.search(skip_pattern, command):
                # Still try to detect, but be aware results may be incomplete
                break

        # Apply each pattern
        for pattern, group_idx in cls.WRITE_PATTERNS:
            for match in re.finditer(pattern, command, re.IGNORECASE):
                try:
                    file_path = match.group(group_idx)

                    # Clean up the path
                    file_path = cls._clean_path(file_path)
                    if not file_path:
                        continue

                    # Resolve to absolute path
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(working_dir, file_path)

                    file_path = os.path.normpath(file_path)

                    # Avoid duplicates
                    if file_path not in files:
                        files.append(file_path)

                except (IndexError, AttributeError):
                    continue

        return files

    @classmethod
    def _clean_path(cls, path: str) -> str:
        """Clean up a detected file path.

        Args:
            path: Raw path string from regex match.

        Returns:
            Cleaned path, or empty string if invalid.
        """
        # Strip quotes
        path = path.strip("'\"")

        # Skip empty paths
        if not path:
            return ""

        # Skip paths that are clearly not files
        if path in ("-", "/dev/null", "/dev/stdout", "/dev/stderr", "/dev/stdin"):
            return ""

        # Skip paths with unresolved variables
        if "$" in path:
            return ""

        # Skip paths that look like flags
        if path.startswith("-"):
            return ""

        return path

    @classmethod
    def is_destructive(cls, command: str) -> bool:
        """Check if command is potentially destructive.

        Args:
            command: Shell command to analyze.

        Returns:
            True if command may delete or overwrite files.
        """
        destructive_patterns = [
            r"\brm\s+",
            r"\brmdir\s+",
            r">\s*[^\s]",  # Overwrite redirect
            r"\bmv\s+",
            r"\bdd\s+",
            r"\btruncate\s+",
        ]

        for pattern in destructive_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True

        return False

    @classmethod
    def get_command_type(cls, command: str) -> str:
        """Categorize the type of file operation.

        Args:
            command: Shell command to analyze.

        Returns:
            Category string: "create", "modify", "delete", "move", "copy", "other"
        """
        # Check patterns in order of specificity
        if re.search(r"\brm\s+|\brmdir\s+", command, re.IGNORECASE):
            return "delete"
        if re.search(r"\bmv\s+", command, re.IGNORECASE):
            return "move"
        if re.search(r"\bcp\s+", command, re.IGNORECASE):
            return "copy"
        if re.search(r"\btouch\s+|\bmkdir\s+", command, re.IGNORECASE):
            return "create"
        if re.search(r">\s*[^\s]|\bsed\s+-i|\bdd\s+|\btee\s+", command, re.IGNORECASE):
            return "modify"

        return "other"
