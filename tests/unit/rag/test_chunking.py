"""Tests for RAG chunking strategies."""

import pytest

from code_forge.rag.chunking import (
    ChunkingStrategy,
    GenericChunker,
    JavaScriptChunker,
    MarkdownChunker,
    PythonCodeChunker,
    detect_language,
    get_chunker,
)
from code_forge.rag.models import ChunkType


class TestGenericChunker:
    """Tests for GenericChunker."""

    def test_name(self) -> None:
        """Test chunker name."""
        chunker = GenericChunker()
        assert chunker.name == "generic"

    def test_chunk_empty_content(self) -> None:
        """Test chunking empty content."""
        chunker = GenericChunker()
        chunks = chunker.chunk("", "test.txt", "doc-123")
        assert chunks == []

    def test_chunk_whitespace_only(self) -> None:
        """Test chunking whitespace-only content."""
        chunker = GenericChunker()
        chunks = chunker.chunk("   \n\n  ", "test.txt", "doc-123")
        assert chunks == []

    def test_chunk_small_content(self) -> None:
        """Test chunking content smaller than chunk size."""
        chunker = GenericChunker(chunk_size=1000)
        content = "Hello, world!\nThis is a test."
        chunks = chunker.chunk(content, "test.txt", "doc-123")
        assert len(chunks) == 1
        assert chunks[0].content == content
        assert chunks[0].chunk_type == ChunkType.GENERIC
        assert chunks[0].document_id == "doc-123"
        assert chunks[0].start_line == 1
        assert chunks[0].end_line == 2

    def test_chunk_large_content(self) -> None:
        """Test chunking content larger than chunk size."""
        chunker = GenericChunker(chunk_size=50, chunk_overlap=10)
        # Create content that will span multiple chunks
        content = "\n".join([f"Line {i}: " + "x" * 50 for i in range(20)])
        chunks = chunker.chunk(content, "test.txt", "doc-123")
        assert len(chunks) > 1
        # All chunks should have correct type
        assert all(c.chunk_type == ChunkType.GENERIC for c in chunks)
        # All chunks should have document_id
        assert all(c.document_id == "doc-123" for c in chunks)

    def test_chunk_preserves_lines(self) -> None:
        """Test that chunks don't split mid-line."""
        chunker = GenericChunker(chunk_size=50)
        content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        chunks = chunker.chunk(content, "test.txt", "doc-123")
        # Check no chunk content ends mid-line (except last)
        for chunk in chunks:
            lines = chunk.content.split("\n")
            # Each line should be complete
            assert all(line == "" or line.startswith("Line") for line in lines)

    def test_chunk_has_token_count(self) -> None:
        """Test that chunks have token count estimated."""
        chunker = GenericChunker()
        content = "Hello world test content"
        chunks = chunker.chunk(content, "test.txt", "doc-123")
        assert len(chunks) == 1
        assert chunks[0].token_count > 0

    def test_chunk_has_metadata(self) -> None:
        """Test that chunks have file path in metadata."""
        chunker = GenericChunker()
        content = "Hello world"
        chunks = chunker.chunk(content, "src/main.py", "doc-123")
        assert len(chunks) == 1
        assert chunks[0].metadata["file_path"] == "src/main.py"


class TestPythonCodeChunker:
    """Tests for PythonCodeChunker."""

    def test_name(self) -> None:
        """Test chunker name."""
        chunker = PythonCodeChunker()
        assert chunker.name == "python"

    def test_chunk_empty_content(self) -> None:
        """Test chunking empty content."""
        chunker = PythonCodeChunker()
        chunks = chunker.chunk("", "test.py", "doc-123")
        assert chunks == []

    def test_chunk_simple_function(self) -> None:
        """Test chunking a simple function."""
        chunker = PythonCodeChunker()
        content = '''def hello():
    """Say hello."""
    print("Hello, world!")
'''
        chunks = chunker.chunk(content, "test.py", "doc-123")
        # Should have function chunk
        func_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
        assert len(func_chunks) == 1
        assert func_chunks[0].name == "hello"

    def test_chunk_async_function(self) -> None:
        """Test chunking an async function."""
        chunker = PythonCodeChunker()
        content = '''async def fetch_data():
    """Fetch data asynchronously."""
    return await get_data()
'''
        chunks = chunker.chunk(content, "test.py", "doc-123")
        func_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
        assert len(func_chunks) == 1
        assert func_chunks[0].name == "fetch_data"
        assert func_chunks[0].metadata.get("is_async") is True

    def test_chunk_class(self) -> None:
        """Test chunking a class."""
        chunker = PythonCodeChunker()
        content = '''class MyClass:
    """A simple class."""

    def __init__(self):
        self.value = 0

    def get_value(self):
        return self.value
'''
        chunks = chunker.chunk(content, "test.py", "doc-123")
        class_chunks = [c for c in chunks if c.chunk_type == ChunkType.CLASS]
        assert len(class_chunks) == 1
        assert class_chunks[0].name == "MyClass"

    def test_chunk_class_with_bases(self) -> None:
        """Test chunking a class with base classes."""
        chunker = PythonCodeChunker()
        content = '''class MyClass(BaseClass, Mixin):
    pass
'''
        chunks = chunker.chunk(content, "test.py", "doc-123")
        class_chunks = [c for c in chunks if c.chunk_type == ChunkType.CLASS]
        assert len(class_chunks) == 1
        assert "BaseClass" in class_chunks[0].metadata.get("bases", [])
        assert "Mixin" in class_chunks[0].metadata.get("bases", [])

    def test_chunk_decorated_function(self) -> None:
        """Test chunking a decorated function."""
        chunker = PythonCodeChunker()
        content = '''@decorator
@another_decorator
def decorated_func():
    pass
'''
        chunks = chunker.chunk(content, "test.py", "doc-123")
        func_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
        assert len(func_chunks) == 1
        # Decorator should be included
        assert "@decorator" in func_chunks[0].content

    def test_chunk_module_level_code(self) -> None:
        """Test chunking module-level code."""
        chunker = PythonCodeChunker()
        content = '''"""Module docstring."""
import os
import sys

CONSTANT = 42

def func():
    pass
'''
        chunks = chunker.chunk(content, "test.py", "doc-123")
        module_chunks = [c for c in chunks if c.chunk_type == ChunkType.MODULE]
        # Should have module-level chunk with imports and constant
        assert len(module_chunks) >= 1

    def test_chunk_syntax_error_fallback(self) -> None:
        """Test fallback to generic chunking on syntax error."""
        chunker = PythonCodeChunker()
        content = '''def broken(
    # Missing closing paren
'''
        # Should not raise, should fall back to generic
        chunks = chunker.chunk(content, "test.py", "doc-123")
        assert len(chunks) >= 1
        # Falls back to generic chunking
        assert chunks[0].chunk_type == ChunkType.GENERIC

    def test_chunk_preserves_line_numbers(self) -> None:
        """Test that line numbers are preserved."""
        chunker = PythonCodeChunker()
        # Use a longer function to avoid minimum token count filter
        content = '''# Comment line 1
# Comment line 2

def func():
    """This is a docstring for the function."""
    value = 42
    result = value * 2
    return result
'''
        chunks = chunker.chunk(content, "test.py", "doc-123")
        func_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
        assert len(func_chunks) == 1
        # Function starts on line 4
        assert func_chunks[0].start_line == 4


class TestMarkdownChunker:
    """Tests for MarkdownChunker."""

    def test_name(self) -> None:
        """Test chunker name."""
        chunker = MarkdownChunker()
        assert chunker.name == "markdown"

    def test_chunk_empty_content(self) -> None:
        """Test chunking empty content."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk("", "test.md", "doc-123")
        assert chunks == []

    def test_chunk_no_headers(self) -> None:
        """Test chunking content without headers."""
        chunker = MarkdownChunker()
        content = "This is just plain text\nwith no headers."
        chunks = chunker.chunk(content, "test.md", "doc-123")
        assert len(chunks) == 1
        assert chunks[0].name == "document"

    def test_chunk_single_section(self) -> None:
        """Test chunking with a single header."""
        # Use min_chunk_size=10 to allow smaller sections in tests
        chunker = MarkdownChunker(min_chunk_size=10)
        content = '''# Introduction

This is the introduction section.
It has multiple lines of content.
We need enough content here to meet the minimum chunk size.
'''
        chunks = chunker.chunk(content, "test.md", "doc-123")
        section_chunks = [c for c in chunks if c.chunk_type == ChunkType.SECTION]
        assert len(section_chunks) == 1
        assert section_chunks[0].name == "Introduction"

    def test_chunk_multiple_sections(self) -> None:
        """Test chunking with multiple headers."""
        # Use min_chunk_size=10 to allow smaller sections in tests
        chunker = MarkdownChunker(min_chunk_size=10)
        content = '''# Section 1

Content for section 1. This section contains important information
about the first topic we are discussing in this document.

## Section 2

Content for section 2. This subsection provides more detail about
a specific aspect of the first section's content.

# Section 3

Content for section 3. This is another major section that covers
an entirely different topic from the previous sections.
'''
        chunks = chunker.chunk(content, "test.md", "doc-123")
        section_chunks = [c for c in chunks if c.chunk_type == ChunkType.SECTION]
        # Should have 3 sections
        assert len(section_chunks) == 3
        names = [c.name for c in section_chunks]
        assert "Section 1" in names
        assert "Section 2" in names
        assert "Section 3" in names

    def test_chunk_preserves_header_level(self) -> None:
        """Test that header level is preserved in metadata."""
        # Use min_chunk_size=10 to allow smaller sections in tests
        chunker = MarkdownChunker(min_chunk_size=10)
        content = '''# H1

This is content for the H1 section with enough text to meet
the minimum chunk size requirements for testing purposes.

## H2

More content for the H2 section which also needs to have enough
text to pass the minimum chunk size filter in our tests.

### H3

Even more content for the H3 section. We need to ensure each
section has sufficient content to be included in results.
'''
        chunks = chunker.chunk(content, "test.md", "doc-123")
        section_chunks = [c for c in chunks if c.chunk_type == ChunkType.SECTION]
        levels = {c.name: c.metadata.get("section_level") for c in section_chunks}
        assert levels.get("H1") == 1
        assert levels.get("H2") == 2
        assert levels.get("H3") == 3

    def test_chunk_preamble_before_header(self) -> None:
        """Test content before first header becomes preamble."""
        chunker = MarkdownChunker(min_chunk_size=10)
        content = '''This is content before any header.
It should become a preamble.

# First Section

Section content.
'''
        chunks = chunker.chunk(content, "test.md", "doc-123")
        preamble_chunks = [c for c in chunks if c.chunk_type == ChunkType.PARAGRAPH]
        assert len(preamble_chunks) == 1
        assert preamble_chunks[0].name == "preamble"

    def test_chunk_large_section_split(self) -> None:
        """Test that large sections are split."""
        chunker = MarkdownChunker(max_chunk_size=50, min_chunk_size=10)
        content = '''# Large Section

''' + "\n".join([f"Line {i}: " + "x" * 40 for i in range(50)])
        chunks = chunker.chunk(content, "test.md", "doc-123")
        # Should have multiple chunks
        assert len(chunks) > 1


class TestJavaScriptChunker:
    """Tests for JavaScriptChunker."""

    def test_name(self) -> None:
        """Test chunker name."""
        chunker = JavaScriptChunker()
        assert chunker.name == "javascript"

    def test_chunk_empty_content(self) -> None:
        """Test chunking empty content."""
        chunker = JavaScriptChunker()
        chunks = chunker.chunk("", "test.js", "doc-123")
        assert chunks == []

    def test_chunk_uses_generic_fallback(self) -> None:
        """Test that JS chunker uses generic fallback."""
        chunker = JavaScriptChunker()
        content = '''function hello() {
    console.log("Hello");
}

const world = () => {
    return "world";
};
'''
        chunks = chunker.chunk(content, "test.js", "doc-123")
        # Should produce chunks (using generic fallback)
        assert len(chunks) >= 1


class TestGetChunker:
    """Tests for get_chunker factory function."""

    def test_get_chunker_by_language_python(self) -> None:
        """Test getting Python chunker by language."""
        chunker = get_chunker(language="python")
        assert isinstance(chunker, PythonCodeChunker)

    def test_get_chunker_by_language_markdown(self) -> None:
        """Test getting Markdown chunker by language."""
        chunker = get_chunker(language="markdown")
        assert isinstance(chunker, MarkdownChunker)

    def test_get_chunker_by_language_javascript(self) -> None:
        """Test getting JavaScript chunker by language."""
        chunker = get_chunker(language="javascript")
        assert isinstance(chunker, JavaScriptChunker)

    def test_get_chunker_by_extension_py(self) -> None:
        """Test getting Python chunker by extension."""
        chunker = get_chunker(file_extension=".py")
        assert isinstance(chunker, PythonCodeChunker)

    def test_get_chunker_by_extension_md(self) -> None:
        """Test getting Markdown chunker by extension."""
        chunker = get_chunker(file_extension=".md")
        assert isinstance(chunker, MarkdownChunker)

    def test_get_chunker_by_extension_js(self) -> None:
        """Test getting JavaScript chunker by extension."""
        chunker = get_chunker(file_extension=".js")
        assert isinstance(chunker, JavaScriptChunker)

    def test_get_chunker_by_extension_ts(self) -> None:
        """Test getting TypeScript chunker by extension."""
        chunker = get_chunker(file_extension=".ts")
        assert isinstance(chunker, JavaScriptChunker)

    def test_get_chunker_by_extension_without_dot(self) -> None:
        """Test getting chunker by extension without leading dot."""
        chunker = get_chunker(file_extension="py")
        assert isinstance(chunker, PythonCodeChunker)

    def test_get_chunker_unknown_language(self) -> None:
        """Test getting generic chunker for unknown language."""
        chunker = get_chunker(language="unknown")
        assert isinstance(chunker, GenericChunker)

    def test_get_chunker_unknown_extension(self) -> None:
        """Test getting generic chunker for unknown extension."""
        chunker = get_chunker(file_extension=".xyz")
        assert isinstance(chunker, GenericChunker)

    def test_get_chunker_default(self) -> None:
        """Test getting generic chunker when no args provided."""
        chunker = get_chunker()
        assert isinstance(chunker, GenericChunker)

    def test_get_chunker_custom_size(self) -> None:
        """Test getting chunker with custom chunk size."""
        chunker = get_chunker(language="python", chunk_size=500, chunk_overlap=50)
        assert isinstance(chunker, PythonCodeChunker)
        assert chunker.max_chunk_size == 500

    def test_get_chunker_language_priority(self) -> None:
        """Test that language takes priority over extension."""
        chunker = get_chunker(language="python", file_extension=".md")
        assert isinstance(chunker, PythonCodeChunker)


class TestDetectLanguage:
    """Tests for detect_language function."""

    def test_detect_python(self) -> None:
        """Test detecting Python language."""
        assert detect_language("main.py") == "python"
        assert detect_language("src/utils.pyi") == "python"

    def test_detect_markdown(self) -> None:
        """Test detecting Markdown language."""
        assert detect_language("README.md") == "markdown"
        assert detect_language("docs/guide.markdown") == "markdown"

    def test_detect_javascript(self) -> None:
        """Test detecting JavaScript language."""
        assert detect_language("app.js") == "javascript"
        assert detect_language("src/index.mjs") == "javascript"

    def test_detect_typescript(self) -> None:
        """Test detecting TypeScript language."""
        assert detect_language("app.ts") == "typescript"
        assert detect_language("components/Button.tsx") == "typescript"

    def test_detect_json(self) -> None:
        """Test detecting JSON."""
        assert detect_language("config.json") == "json"

    def test_detect_yaml(self) -> None:
        """Test detecting YAML."""
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("config.yml") == "yaml"

    def test_detect_unknown(self) -> None:
        """Test unknown extension returns None."""
        assert detect_language("file.xyz") is None
        assert detect_language("file") is None


class TestChunkingStrategyProtocol:
    """Tests to verify chunkers implement the protocol correctly."""

    @pytest.mark.parametrize(
        "chunker_class",
        [GenericChunker, PythonCodeChunker, MarkdownChunker, JavaScriptChunker],
    )
    def test_chunker_has_required_methods(
        self, chunker_class: type[ChunkingStrategy]
    ) -> None:
        """Test that all chunkers have required methods."""
        chunker = chunker_class()
        assert hasattr(chunker, "chunk")
        assert hasattr(chunker, "name")
        assert callable(chunker.chunk)

    @pytest.mark.parametrize(
        "chunker_class",
        [GenericChunker, PythonCodeChunker, MarkdownChunker, JavaScriptChunker],
    )
    def test_chunker_returns_list_of_chunks(
        self, chunker_class: type[ChunkingStrategy]
    ) -> None:
        """Test that all chunkers return list of Chunk objects."""
        from code_forge.rag.models import Chunk

        chunker = chunker_class()
        content = "Some content\nwith lines"
        chunks = chunker.chunk(content, "test.txt", "doc-123")
        assert isinstance(chunks, list)
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
