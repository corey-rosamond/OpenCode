"""Text chunking strategies for RAG system.

This module provides different chunking strategies for splitting documents
into smaller pieces suitable for embedding and retrieval:

- PythonCodeChunker: AST-aware chunking for Python files
- MarkdownChunker: Section-based chunking for Markdown files
- GenericChunker: Character-based chunking for other files

Example:
    from code_forge.rag.chunking import get_chunker

    # Get appropriate chunker for file type
    chunker = get_chunker("python")
    chunks = chunker.chunk(content, file_path="src/main.py", document_id="doc-123")

    for chunk in chunks:
        print(f"{chunk.chunk_type}: {chunk.name} ({chunk.token_count} tokens)")
"""

from __future__ import annotations

import ast
import logging
import re
import uuid
from abc import ABC, abstractmethod

from .models import Chunk, ChunkType

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses a simple heuristic of ~4 characters per token.
    This is approximate but avoids loading a tokenizer.

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count.
    """
    return max(1, len(text) // 4)


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies.

    All chunking strategies must implement the chunk() method to split
    document content into smaller pieces suitable for embedding.
    """

    @abstractmethod
    def chunk(
        self,
        content: str,
        file_path: str,
        document_id: str,
    ) -> list[Chunk]:
        """Split content into chunks.

        Args:
            content: The document content to chunk.
            file_path: Path to the source file (for context).
            document_id: ID of the parent document.

        Returns:
            List of Chunk objects.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the strategy name."""
        ...


class GenericChunker(ChunkingStrategy):
    """Character-based chunking strategy.

    Splits text into chunks of approximately equal size with overlap.
    Used as a fallback when no specialized chunker is available.

    Attributes:
        chunk_size: Target tokens per chunk.
        chunk_overlap: Overlap tokens between chunks.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ) -> None:
        """Initialize the generic chunker.

        Args:
            chunk_size: Target tokens per chunk.
            chunk_overlap: Overlap tokens between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Approximate characters per token
        self._chars_per_token = 4

    @property
    def name(self) -> str:
        """Get the strategy name."""
        return "generic"

    def chunk(
        self,
        content: str,
        file_path: str,
        document_id: str,
    ) -> list[Chunk]:
        """Split content into fixed-size chunks with overlap.

        Args:
            content: The document content to chunk.
            file_path: Path to the source file.
            document_id: ID of the parent document.

        Returns:
            List of Chunk objects.
        """

        if not content.strip():
            return []

        chunks: list[Chunk] = []
        lines = content.splitlines(keepends=True)

        # Calculate target size in characters
        target_chars = self.chunk_size * self._chars_per_token
        overlap_chars = self.chunk_overlap * self._chars_per_token

        current_chunk: list[str] = []
        current_size = 0
        chunk_start_line = 1

        for line_num, line in enumerate(lines, start=1):
            line_len = len(line)

            # If adding this line would exceed target, finalize current chunk
            if current_size + line_len > target_chars and current_chunk:
                chunk_content = "".join(current_chunk)
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        chunk_type=ChunkType.GENERIC,
                        content=chunk_content,
                        start_line=chunk_start_line,
                        end_line=line_num - 1,
                        token_count=_estimate_tokens(chunk_content),
                        metadata={"file_path": file_path},
                    )
                )

                # Start new chunk with overlap
                overlap_lines = self._get_overlap_lines(
                    current_chunk, overlap_chars
                )
                current_chunk = overlap_lines
                current_size = sum(len(line) for line in current_chunk)
                chunk_start_line = line_num - len(overlap_lines)

            current_chunk.append(line)
            current_size += line_len

        # Don't forget the last chunk
        if current_chunk:
            chunk_content = "".join(current_chunk)
            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_type=ChunkType.GENERIC,
                    content=chunk_content,
                    start_line=chunk_start_line,
                    end_line=len(lines),
                    token_count=_estimate_tokens(chunk_content),
                    metadata={"file_path": file_path},
                )
            )

        return chunks

    def _get_overlap_lines(
        self,
        lines: list[str],
        overlap_chars: int,
    ) -> list[str]:
        """Get lines from the end to use as overlap.

        Args:
            lines: List of lines in the current chunk.
            overlap_chars: Target overlap in characters.

        Returns:
            Lines to include as overlap in next chunk.
        """
        if not lines:
            return []

        overlap_lines: list[str] = []
        char_count = 0

        for line in reversed(lines):
            if char_count + len(line) > overlap_chars:
                break
            overlap_lines.insert(0, line)
            char_count += len(line)

        return overlap_lines


class PythonCodeChunker(ChunkingStrategy):
    """AST-aware chunking strategy for Python code.

    Parses Python source code and creates chunks based on the AST structure:
    - Functions and methods become individual chunks
    - Classes become chunks (with nested methods as separate chunks)
    - Module-level code becomes a chunk

    Falls back to generic chunking if AST parsing fails.

    Attributes:
        max_chunk_size: Maximum tokens per chunk.
        fallback_chunker: Chunker to use if AST parsing fails.
    """

    def __init__(
        self,
        max_chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ) -> None:
        """Initialize the Python chunker.

        Args:
            max_chunk_size: Maximum tokens per chunk.
            chunk_overlap: Overlap for fallback chunking.
        """
        self.max_chunk_size = max_chunk_size
        self._fallback = GenericChunker(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
        )

    @property
    def name(self) -> str:
        """Get the strategy name."""
        return "python"

    def chunk(
        self,
        content: str,
        file_path: str,
        document_id: str,
    ) -> list[Chunk]:
        """Split Python code into AST-based chunks.

        Args:
            content: Python source code.
            file_path: Path to the source file.
            document_id: ID of the parent document.

        Returns:
            List of Chunk objects.
        """

        if not content.strip():
            return []

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.debug(f"AST parse failed for {file_path}: {e}, using fallback")
            return self._fallback.chunk(content, file_path, document_id)

        chunks: list[Chunk] = []
        lines = content.splitlines()

        # Track which lines are covered by functions/classes
        covered_lines: set[int] = set()

        # Extract functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                chunk = self._extract_function(
                    node, lines, document_id, file_path
                )
                if chunk:
                    chunks.append(chunk)
                    covered_lines.update(
                        range(chunk.start_line, chunk.end_line + 1)
                    )

            elif isinstance(node, ast.ClassDef):
                chunk = self._extract_class(
                    node, lines, document_id, file_path
                )
                if chunk:
                    chunks.append(chunk)
                    covered_lines.update(
                        range(chunk.start_line, chunk.end_line + 1)
                    )

        # Extract module-level code (imports, constants, etc.)
        module_chunk = self._extract_module_level(
            tree, lines, covered_lines, document_id, file_path
        )
        if module_chunk:
            chunks.append(module_chunk)

        # If no chunks were created, fall back to generic
        if not chunks:
            return self._fallback.chunk(content, file_path, document_id)

        # Sort by line number
        chunks.sort(key=lambda c: c.start_line)

        return chunks

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: list[str],
        document_id: str,
        file_path: str,
    ) -> Chunk | None:
        """Extract a function as a chunk.

        Args:
            node: AST function node.
            lines: Source lines.
            document_id: Parent document ID.
            file_path: Source file path.

        Returns:
            Chunk for the function, or None if too small.
        """

        start_line = node.lineno
        end_line = node.end_lineno or node.lineno

        # Get function content
        func_lines = lines[start_line - 1 : end_line]
        content = "\n".join(func_lines)

        if not content.strip():
            return None

        # Get decorators if present
        if node.decorator_list:
            first_decorator = node.decorator_list[0]
            start_line = first_decorator.lineno
            func_lines = lines[start_line - 1 : end_line]
            content = "\n".join(func_lines)

        token_count = _estimate_tokens(content)

        # Skip very small functions
        if token_count < 10:
            return None

        # Determine if it's a method or function
        is_async = isinstance(node, ast.AsyncFunctionDef)
        func_type = "async function" if is_async else "function"

        return Chunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            chunk_type=ChunkType.FUNCTION,
            content=content,
            start_line=start_line,
            end_line=end_line,
            token_count=token_count,
            name=node.name,
            metadata={
                "file_path": file_path,
                "function_type": func_type,
                "is_async": is_async,
            },
        )

    def _extract_class(
        self,
        node: ast.ClassDef,
        lines: list[str],
        document_id: str,
        file_path: str,
    ) -> Chunk | None:
        """Extract a class definition as a chunk.

        Includes the class signature, docstring, and class-level attributes.
        Methods are extracted separately.

        Args:
            node: AST class node.
            lines: Source lines.
            document_id: Parent document ID.
            file_path: Source file path.

        Returns:
            Chunk for the class, or None if too small.
        """

        start_line = node.lineno
        end_line = node.end_lineno or node.lineno

        # Get decorators if present
        if node.decorator_list:
            first_decorator = node.decorator_list[0]
            start_line = first_decorator.lineno

        # Get full class content
        class_lines = lines[start_line - 1 : end_line]
        content = "\n".join(class_lines)

        if not content.strip():
            return None

        token_count = _estimate_tokens(content)

        # Get base classes
        bases = [self._get_node_name(base) for base in node.bases]

        return Chunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            chunk_type=ChunkType.CLASS,
            content=content,
            start_line=start_line,
            end_line=end_line,
            token_count=token_count,
            name=node.name,
            metadata={
                "file_path": file_path,
                "bases": bases,
            },
        )

    def _extract_module_level(
        self,
        _tree: ast.Module,
        lines: list[str],
        covered_lines: set[int],
        document_id: str,
        file_path: str,
    ) -> Chunk | None:
        """Extract module-level code (imports, constants, etc.).

        Args:
            tree: AST module.
            lines: Source lines.
            covered_lines: Lines already covered by other chunks.
            document_id: Parent document ID.
            file_path: Source file path.

        Returns:
            Chunk for module-level code, or None if empty.
        """

        # Collect module-level lines (not in functions/classes)
        module_lines: list[tuple[int, str]] = []

        for i, line in enumerate(lines, start=1):
            if i not in covered_lines and line.strip():
                module_lines.append((i, line))

        if not module_lines:
            return None

        # Group consecutive lines
        if not module_lines:
            return None

        content_lines = [line for _, line in module_lines]
        content = "\n".join(content_lines)

        if not content.strip():
            return None

        token_count = _estimate_tokens(content)

        # Skip very small module chunks
        if token_count < 5:
            return None

        start_line = module_lines[0][0]
        end_line = module_lines[-1][0]

        return Chunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            chunk_type=ChunkType.MODULE,
            content=content,
            start_line=start_line,
            end_line=end_line,
            token_count=token_count,
            name="module",
            metadata={"file_path": file_path},
        )

    @staticmethod
    def _get_node_name(node: ast.expr) -> str:
        """Get name from an AST node.

        Args:
            node: AST expression node.

        Returns:
            String representation of the node.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{PythonCodeChunker._get_node_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{PythonCodeChunker._get_node_name(node.value)}[...]"
        else:
            return "<unknown>"


class MarkdownChunker(ChunkingStrategy):
    """Section-based chunking strategy for Markdown files.

    Splits Markdown content based on headers, creating chunks for each
    section. Handles nested headers and preserves section hierarchy.

    Attributes:
        max_chunk_size: Maximum tokens per chunk.
        min_chunk_size: Minimum tokens to create a chunk.
    """

    # Regex to match Markdown headers
    _HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        max_chunk_size: int = 1000,
        min_chunk_size: int = 50,
        chunk_overlap: int = 100,
    ) -> None:
        """Initialize the Markdown chunker.

        Args:
            max_chunk_size: Maximum tokens per chunk.
            min_chunk_size: Minimum tokens for a chunk.
            chunk_overlap: Overlap for fallback chunking.
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self._fallback = GenericChunker(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
        )

    @property
    def name(self) -> str:
        """Get the strategy name."""
        return "markdown"

    def chunk(
        self,
        content: str,
        file_path: str,
        document_id: str,
    ) -> list[Chunk]:
        """Split Markdown into section-based chunks.

        Args:
            content: Markdown content.
            file_path: Path to the source file.
            document_id: ID of the parent document.

        Returns:
            List of Chunk objects.
        """
        if not content.strip():
            return []

        lines = content.splitlines()
        chunks: list[Chunk] = []

        # Find all headers with their positions
        headers: list[tuple[int, int, str]] = []  # (line_num, level, title)

        for i, line in enumerate(lines):
            match = self._HEADER_PATTERN.match(line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                headers.append((i + 1, level, title))

        if not headers:
            # No headers, treat as single section or use generic
            if _estimate_tokens(content) > self.max_chunk_size:
                return self._fallback.chunk(content, file_path, document_id)

            return [
                Chunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_type=ChunkType.SECTION,
                    content=content,
                    start_line=1,
                    end_line=len(lines),
                    token_count=_estimate_tokens(content),
                    name="document",
                    metadata={"file_path": file_path},
                )
            ]

        # Create chunks for each section
        for i, (line_num, level, title) in enumerate(headers):
            # Find end of this section (next header of same or higher level)
            end_line = len(lines)
            for next_line, next_level, _ in headers[i + 1 :]:
                if next_level <= level:
                    end_line = next_line - 1
                    break
                # For subsections, include them in parent
                end_line = next_line - 1

            # Actually, simpler: section ends at next header
            if i + 1 < len(headers):
                end_line = headers[i + 1][0] - 1

            # Extract section content
            section_lines = lines[line_num - 1 : end_line]
            section_content = "\n".join(section_lines)

            if not section_content.strip():
                continue

            token_count = _estimate_tokens(section_content)

            # Skip very small sections
            if token_count < self.min_chunk_size:
                continue

            # If section is too large, split it
            if token_count > self.max_chunk_size:
                sub_chunks = self._fallback.chunk(
                    section_content,
                    file_path,
                    document_id,
                )
                # Update metadata for sub-chunks
                for j, sub_chunk in enumerate(sub_chunks):
                    sub_chunk.name = f"{title} (part {j + 1})"
                    sub_chunk.chunk_type = ChunkType.SECTION
                    sub_chunk.start_line = line_num + sub_chunk.start_line - 1
                    sub_chunk.end_line = line_num + sub_chunk.end_line - 1
                    sub_chunk.metadata["section_title"] = title
                    sub_chunk.metadata["section_level"] = level
                chunks.extend(sub_chunks)
            else:
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        chunk_type=ChunkType.SECTION,
                        content=section_content,
                        start_line=line_num,
                        end_line=end_line,
                        token_count=token_count,
                        name=title,
                        metadata={
                            "file_path": file_path,
                            "section_level": level,
                        },
                    )
                )

        # Handle content before first header
        if headers and headers[0][0] > 1:
            preamble_lines = lines[: headers[0][0] - 1]
            preamble_content = "\n".join(preamble_lines)

            if preamble_content.strip():
                token_count = _estimate_tokens(preamble_content)
                if token_count >= self.min_chunk_size:
                    chunks.insert(
                        0,
                        Chunk(
                            id=str(uuid.uuid4()),
                            document_id=document_id,
                            chunk_type=ChunkType.PARAGRAPH,
                            content=preamble_content,
                            start_line=1,
                            end_line=headers[0][0] - 1,
                            token_count=token_count,
                            name="preamble",
                            metadata={"file_path": file_path},
                        ),
                    )

        # Sort by line number
        chunks.sort(key=lambda c: c.start_line)

        return chunks


class JavaScriptChunker(ChunkingStrategy):
    """Chunking strategy for JavaScript/TypeScript files.

    Uses regex-based parsing to identify functions, classes, and exports.
    Falls back to generic chunking for complex cases.

    Note: This is a simplified chunker that doesn't use a full JS parser.
    """

    # Patterns for JS/TS constructs
    _FUNCTION_PATTERN = re.compile(
        r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
        re.MULTILINE,
    )
    _ARROW_PATTERN = re.compile(
        r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    )
    _CLASS_PATTERN = re.compile(
        r"^(?:export\s+)?class\s+(\w+)",
        re.MULTILINE,
    )

    def __init__(
        self,
        max_chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ) -> None:
        """Initialize the JavaScript chunker.

        Args:
            max_chunk_size: Maximum tokens per chunk.
            chunk_overlap: Overlap for fallback chunking.
        """
        self.max_chunk_size = max_chunk_size
        self._fallback = GenericChunker(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
        )

    @property
    def name(self) -> str:
        """Get the strategy name."""
        return "javascript"

    def chunk(
        self,
        content: str,
        file_path: str,
        document_id: str,
    ) -> list[Chunk]:
        """Split JavaScript/TypeScript into chunks.

        For now, uses generic chunking as a robust fallback.
        A full implementation would use a proper JS parser.

        Args:
            content: JavaScript/TypeScript content.
            file_path: Path to the source file.
            document_id: ID of the parent document.

        Returns:
            List of Chunk objects.
        """
        # For robustness, use generic chunking
        # A full implementation would use esprima or similar
        return self._fallback.chunk(content, file_path, document_id)


# Mapping of file extensions to chunker classes
_EXTENSION_TO_CHUNKER: dict[str, type[ChunkingStrategy]] = {
    ".py": PythonCodeChunker,
    ".pyi": PythonCodeChunker,
    ".md": MarkdownChunker,
    ".markdown": MarkdownChunker,
    ".js": JavaScriptChunker,
    ".jsx": JavaScriptChunker,
    ".ts": JavaScriptChunker,
    ".tsx": JavaScriptChunker,
    ".mjs": JavaScriptChunker,
}

# Mapping of language names to chunker classes
_LANGUAGE_TO_CHUNKER: dict[str, type[ChunkingStrategy]] = {
    "python": PythonCodeChunker,
    "markdown": MarkdownChunker,
    "javascript": JavaScriptChunker,
    "typescript": JavaScriptChunker,
}


def get_chunker(
    language: str | None = None,
    file_extension: str | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
) -> ChunkingStrategy:
    """Get appropriate chunker for a file type.

    Args:
        language: Language name (e.g., "python", "markdown").
        file_extension: File extension including dot (e.g., ".py").
        chunk_size: Target chunk size in tokens.
        chunk_overlap: Overlap between chunks in tokens.

    Returns:
        Appropriate ChunkingStrategy instance.
    """
    chunker_class: type[ChunkingStrategy] | None = None

    # Try language first
    if language:
        chunker_class = _LANGUAGE_TO_CHUNKER.get(language.lower())

    # Then try extension
    if not chunker_class and file_extension:
        ext = file_extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        chunker_class = _EXTENSION_TO_CHUNKER.get(ext)

    # Default to generic
    if not chunker_class:
        chunker_class = GenericChunker

    # Create instance with appropriate arguments
    if chunker_class == GenericChunker:
        return GenericChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif chunker_class == MarkdownChunker:
        return MarkdownChunker(
            max_chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    elif chunker_class == PythonCodeChunker:
        return PythonCodeChunker(
            max_chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    elif chunker_class == JavaScriptChunker:
        return JavaScriptChunker(
            max_chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    else:
        # Fallback to generic for unknown chunkers
        return GenericChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def detect_language(file_path: str) -> str | None:
    """Detect programming language from file path.

    Args:
        file_path: Path to the file.

    Returns:
        Language name or None if unknown.
    """
    from pathlib import Path

    ext = Path(file_path).suffix.lower()

    extension_to_language: dict[str, str] = {
        ".py": "python",
        ".pyi": "python",
        ".md": "markdown",
        ".markdown": "markdown",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mjs": "javascript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".rst": "restructuredtext",
        ".txt": "text",
    }

    return extension_to_language.get(ext)
