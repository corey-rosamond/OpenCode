"""HTML parser edge case tests.

Tests comprehensive edge cases for HTML parsing including
malformed HTML, special characters, relative URLs, and XSS sanitization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from code_forge.web.fetch.parser import HTMLParser

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def parser() -> HTMLParser:
    """Create HTMLParser instance."""
    return HTMLParser()


# =============================================================================
# Test to_text() Method
# =============================================================================


class TestToText:
    """Tests for to_text() conversion."""

    def test_basic_paragraph(self, parser: HTMLParser) -> None:
        """Basic paragraph converts to text."""
        html = "<p>Hello, world!</p>"
        result = parser.to_text(html)
        assert result == "Hello, world!"

    def test_nested_elements(self, parser: HTMLParser) -> None:
        """Nested elements preserve text content."""
        html = "<div><p><span>Nested</span> text</p></div>"
        result = parser.to_text(html)
        assert "Nested" in result
        assert "text" in result

    def test_strips_scripts(self, parser: HTMLParser) -> None:
        """Script tags are removed."""
        html = "<p>Before</p><script>alert('xss')</script><p>After</p>"
        result = parser.to_text(html)
        assert "Before" in result
        assert "After" in result
        assert "alert" not in result
        assert "script" not in result

    def test_strips_styles(self, parser: HTMLParser) -> None:
        """Style tags are removed."""
        html = "<p>Content</p><style>.hidden{display:none}</style>"
        result = parser.to_text(html)
        assert "Content" in result
        assert "display" not in result
        assert "hidden" not in result

    def test_strips_nav_footer_aside(self, parser: HTMLParser) -> None:
        """Nav, footer, and aside are removed."""
        html = """
        <nav>Navigation</nav>
        <main>Main Content</main>
        <footer>Footer</footer>
        <aside>Sidebar</aside>
        """
        result = parser.to_text(html)
        assert "Main Content" in result
        assert "Navigation" not in result
        assert "Footer" not in result
        assert "Sidebar" not in result

    def test_collapses_whitespace(self, parser: HTMLParser) -> None:
        """Multiple newlines are collapsed."""
        html = "<p>First</p>\n\n\n\n\n<p>Second</p>"
        result = parser.to_text(html)
        assert result.count("\n\n\n") == 0

    def test_empty_html(self, parser: HTMLParser) -> None:
        """Empty HTML returns empty string."""
        result = parser.to_text("")
        assert result == ""

    def test_html_entities(self, parser: HTMLParser) -> None:
        """HTML entities are decoded."""
        html = "<p>&lt;hello&gt; &amp; &quot;world&quot;</p>"
        result = parser.to_text(html)
        assert "<hello>" in result or "&lt;hello&gt;" in result  # Depends on parser
        assert "&" in result or "&amp;" in result

    def test_unicode_content(self, parser: HTMLParser) -> None:
        """Unicode content is preserved."""
        html = "<p>日本語テスト 🎉 Ñoño</p>"
        result = parser.to_text(html)
        assert "日本語" in result
        assert "🎉" in result
        assert "Ñoño" in result


# =============================================================================
# Test to_markdown() Method
# =============================================================================


class TestToMarkdown:
    """Tests for to_markdown() conversion."""

    def test_headings(self, parser: HTMLParser) -> None:
        """Headings convert to markdown headers."""
        html = "<h1>Title</h1><h2>Subtitle</h2><h3>Section</h3>"
        result = parser.to_markdown(html)
        assert "#" in result  # At least one header marker

    def test_bold_and_italic(self, parser: HTMLParser) -> None:
        """Bold and italic are preserved."""
        html = "<p><strong>bold</strong> and <em>italic</em></p>"
        result = parser.to_markdown(html)
        assert "**bold**" in result or "**" in result
        assert "_italic_" in result or "*italic*" in result or "_" in result

    def test_links_preserved(self, parser: HTMLParser) -> None:
        """Links are converted to markdown format."""
        html = '<p>Click <a href="https://example.com">here</a></p>'
        result = parser.to_markdown(html)
        assert "example.com" in result
        assert "here" in result

    def test_lists(self, parser: HTMLParser) -> None:
        """Lists convert to markdown."""
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = parser.to_markdown(html)
        assert "Item 1" in result
        assert "Item 2" in result

    def test_code_blocks(self, parser: HTMLParser) -> None:
        """Code blocks are handled."""
        html = "<pre><code>def hello():\n    pass</code></pre>"
        result = parser.to_markdown(html)
        assert "hello" in result
        assert "pass" in result

    def test_inline_code(self, parser: HTMLParser) -> None:
        """Inline code is handled."""
        html = "<p>Use <code>print()</code> to output</p>"
        result = parser.to_markdown(html)
        assert "print" in result

    def test_strips_nav_footer(self, parser: HTMLParser) -> None:
        """Nav and footer are stripped from markdown."""
        html = "<nav>Menu</nav><p>Content</p><footer>Copyright</footer>"
        result = parser.to_markdown(html)
        assert "Content" in result
        assert "Menu" not in result
        assert "Copyright" not in result

    def test_blockquotes(self, parser: HTMLParser) -> None:
        """Blockquotes are converted."""
        html = "<blockquote>Famous quote</blockquote>"
        result = parser.to_markdown(html)
        assert "Famous quote" in result


# =============================================================================
# Test Relative Link Resolution
# =============================================================================


class TestRelativeLinkResolution:
    """Tests for relative URL resolution."""

    def test_absolute_link_unchanged(self, parser: HTMLParser) -> None:
        """Absolute links remain unchanged."""
        html = '<a href="https://example.com/page">Link</a>'
        result = parser.parse(html, base_url="https://other.com")
        assert result.links[0]["url"] == "https://example.com/page"

    def test_relative_link_resolved(self, parser: HTMLParser) -> None:
        """Relative links are resolved against base URL."""
        html = '<a href="/page">Link</a>'
        result = parser.parse(html, base_url="https://example.com/subdir/")
        assert result.links[0]["url"] == "https://example.com/page"

    def test_relative_path_link(self, parser: HTMLParser) -> None:
        """Relative path links are resolved."""
        html = '<a href="sibling.html">Link</a>'
        result = parser.parse(html, base_url="https://example.com/dir/current.html")
        assert "example.com" in result.links[0]["url"]
        assert "sibling.html" in result.links[0]["url"]

    def test_parent_directory_link(self, parser: HTMLParser) -> None:
        """Parent directory links are resolved."""
        html = '<a href="../parent.html">Link</a>'
        result = parser.parse(html, base_url="https://example.com/dir/subdir/")
        assert "example.com" in result.links[0]["url"]

    def test_protocol_relative_link(self, parser: HTMLParser) -> None:
        """Protocol-relative links are resolved."""
        html = '<a href="//cdn.example.com/resource">Link</a>'
        result = parser.parse(html, base_url="https://example.com/")
        assert "cdn.example.com" in result.links[0]["url"]

    def test_image_src_resolution(self, parser: HTMLParser) -> None:
        """Image src attributes are resolved."""
        html = '<img src="/images/photo.jpg" alt="Photo">'
        result = parser.parse(html, base_url="https://example.com/page/")
        assert result.images[0]["src"] == "https://example.com/images/photo.jpg"

    def test_no_base_url(self, parser: HTMLParser) -> None:
        """Links are unchanged without base URL."""
        html = '<a href="/page">Link</a>'
        result = parser.parse(html, base_url=None)
        assert result.links[0]["url"] == "/page"


# =============================================================================
# Test Malformed HTML Handling
# =============================================================================


class TestMalformedHTML:
    """Tests for malformed HTML handling."""

    def test_missing_closing_tags(self, parser: HTMLParser) -> None:
        """Missing closing tags are handled."""
        html = "<p>Paragraph without closing tag<p>Another paragraph"
        result = parser.to_text(html)
        assert "Paragraph" in result
        assert "Another" in result

    def test_mismatched_tags(self, parser: HTMLParser) -> None:
        """Mismatched tags are handled."""
        html = "<div><p>Content</div></p>"
        result = parser.to_text(html)
        assert "Content" in result

    def test_unclosed_attributes(self, parser: HTMLParser) -> None:
        """Unclosed attributes are handled."""
        html = '<a href="http://example.com>Link text</a>'
        result = parser.parse(html)
        # Should not crash, text should be extractable
        assert result is not None

    def test_invalid_nesting(self, parser: HTMLParser) -> None:
        """Invalid nesting is handled."""
        html = "<p><div>Invalid nesting</div></p>"
        result = parser.to_text(html)
        assert "Invalid nesting" in result

    def test_bare_text(self, parser: HTMLParser) -> None:
        """Bare text without tags is handled."""
        html = "Just plain text without any HTML tags"
        result = parser.to_text(html)
        assert "Just plain text" in result

    def test_only_doctype(self, parser: HTMLParser) -> None:
        """Only doctype declaration is handled."""
        html = "<!DOCTYPE html>"
        result = parser.to_text(html)
        assert result == ""

    def test_comments_only(self, parser: HTMLParser) -> None:
        """HTML with only comments is handled."""
        html = "<!-- This is a comment -->"
        result = parser.to_text(html)
        assert result == ""


# =============================================================================
# Test Nested Structures
# =============================================================================


class TestNestedStructures:
    """Tests for deeply nested HTML structures."""

    def test_deeply_nested_divs(self, parser: HTMLParser) -> None:
        """Deeply nested divs are handled."""
        html = "<div>" * 50 + "Deep content" + "</div>" * 50
        result = parser.to_text(html)
        assert "Deep content" in result

    def test_nested_lists(self, parser: HTMLParser) -> None:
        """Nested lists are handled."""
        html = """
        <ul>
            <li>Item 1
                <ul>
                    <li>Sub-item 1.1</li>
                    <li>Sub-item 1.2</li>
                </ul>
            </li>
            <li>Item 2</li>
        </ul>
        """
        result = parser.to_text(html)
        assert "Item 1" in result
        assert "Sub-item 1.1" in result
        assert "Item 2" in result

    def test_nested_tables(self, parser: HTMLParser) -> None:
        """Nested tables are handled."""
        html = """
        <table>
            <tr>
                <td>
                    <table>
                        <tr><td>Nested cell</td></tr>
                    </table>
                </td>
            </tr>
        </table>
        """
        result = parser.to_text(html)
        assert "Nested cell" in result


# =============================================================================
# Test Special Characters in Content
# =============================================================================


class TestSpecialCharacters:
    """Tests for special character handling."""

    def test_html_entities(self, parser: HTMLParser) -> None:
        """HTML entities are handled."""
        html = "<p>&nbsp;&copy; 2024 &mdash; Test</p>"
        result = parser.to_text(html)
        # Should decode entities
        assert "2024" in result

    def test_numeric_entities(self, parser: HTMLParser) -> None:
        """Numeric entities are handled."""
        html = "<p>&#169; &#8212; &#x2022;</p>"
        result = parser.to_text(html)
        assert result is not None

    def test_less_than_greater_than(self, parser: HTMLParser) -> None:
        """< and > in content are handled."""
        html = "<p>if (x &lt; 10 &amp;&amp; y &gt; 5)</p>"
        result = parser.to_text(html)
        assert "x" in result
        assert "10" in result

    def test_emoji_content(self, parser: HTMLParser) -> None:
        """Emoji content is preserved."""
        html = "<p>Great job! 👍🎉🚀</p>"
        result = parser.to_text(html)
        assert "👍" in result
        assert "🎉" in result

    def test_newlines_in_pre(self, parser: HTMLParser) -> None:
        """Newlines in pre tags are preserved."""
        html = "<pre>Line 1\nLine 2\nLine 3</pre>"
        result = parser.to_text(html)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result


# =============================================================================
# Test Empty Elements
# =============================================================================


class TestEmptyElements:
    """Tests for empty element handling."""

    def test_empty_paragraph(self, parser: HTMLParser) -> None:
        """Empty paragraphs are handled."""
        html = "<p></p><p>Content</p><p></p>"
        result = parser.to_text(html)
        assert "Content" in result

    def test_empty_div(self, parser: HTMLParser) -> None:
        """Empty divs are handled."""
        html = "<div></div><div>Content</div>"
        result = parser.to_text(html)
        assert "Content" in result

    def test_self_closing_tags(self, parser: HTMLParser) -> None:
        """Self-closing tags are handled."""
        html = "<p>Before<br/>After</p><hr/><p>End</p>"
        result = parser.to_text(html)
        assert "Before" in result
        assert "After" in result

    def test_empty_links(self, parser: HTMLParser) -> None:
        """Empty links are handled."""
        html = '<a href="https://example.com"></a><a href="https://other.com">Text</a>'
        result = parser.parse(html)
        assert len(result.links) == 2
        assert result.links[1]["text"] == "Text"


# =============================================================================
# Test Base URL Handling
# =============================================================================


class TestBaseURLHandling:
    """Tests for base URL handling edge cases."""

    def test_empty_base_url(self, parser: HTMLParser) -> None:
        """Empty base URL is handled."""
        html = '<a href="/page">Link</a>'
        result = parser.parse(html, base_url="")
        assert result.links[0]["url"] == "/page"

    def test_base_url_with_fragment(self, parser: HTMLParser) -> None:
        """Base URL with fragment is handled."""
        html = '<a href="page.html">Link</a>'
        result = parser.parse(html, base_url="https://example.com/dir/#section")
        assert "example.com" in result.links[0]["url"]

    def test_base_url_with_query(self, parser: HTMLParser) -> None:
        """Base URL with query string is handled."""
        html = '<a href="page.html">Link</a>'
        result = parser.parse(html, base_url="https://example.com/dir/?param=value")
        assert "example.com" in result.links[0]["url"]


# =============================================================================
# Test Encoding Detection
# =============================================================================


class TestEncodingDetection:
    """Tests for encoding detection and handling."""

    def test_utf8_content(self, parser: HTMLParser) -> None:
        """UTF-8 content is handled."""
        html = '<meta charset="UTF-8"><p>Ñ é ü ß</p>'
        result = parser.to_text(html)
        assert "Ñ" in result

    def test_mixed_encodings(self, parser: HTMLParser) -> None:
        """Mixed encoding declarations are handled."""
        html = '''
        <meta charset="UTF-8">
        <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
        <p>Content</p>
        '''
        result = parser.to_text(html)
        assert "Content" in result


# =============================================================================
# Test XSS Sanitization
# =============================================================================


class TestXSSSanitization:
    """Tests for XSS attack prevention."""

    def test_javascript_url_removed(self, parser: HTMLParser) -> None:
        """javascript: URLs are removed."""
        html = '<a href="javascript:alert(1)">Click me</a>'
        result = parser.extract_main_content(html)
        assert "javascript:" not in result.lower()

    def test_onclick_handler_removed(self, parser: HTMLParser) -> None:
        """onclick handlers are removed."""
        html = '<button onclick="alert(1)">Click</button>'
        result = parser.extract_main_content(html)
        assert "onclick" not in result.lower()

    def test_onerror_handler_removed(self, parser: HTMLParser) -> None:
        """onerror handlers are removed."""
        html = '<img src="x" onerror="alert(1)">'
        result = parser.extract_main_content(html)
        assert "onerror" not in result.lower()

    def test_onload_handler_removed(self, parser: HTMLParser) -> None:
        """onload handlers are removed."""
        html = '<body onload="alert(1)"><p>Content</p></body>'
        result = parser.extract_main_content(html)
        assert "onload" not in result.lower()

    def test_script_tags_removed(self, parser: HTMLParser) -> None:
        """Script tags are removed from main content."""
        html = '<p>Safe</p><script>evil()</script><p>Content</p>'
        result = parser.extract_main_content(html)
        assert "script" not in result.lower()
        assert "evil" not in result

    def test_iframe_removed(self, parser: HTMLParser) -> None:
        """Iframes are removed from main content."""
        html = '<p>Content</p><iframe src="https://evil.com"></iframe>'
        result = parser.extract_main_content(html)
        assert "iframe" not in result.lower()

    def test_data_url_with_javascript(self, parser: HTMLParser) -> None:
        """data: URLs with javascript are handled."""
        html = '<a href="data:text/html,<script>alert(1)</script>">Link</a>'
        # Should not crash
        result = parser.parse(html)
        assert result is not None


# =============================================================================
# Test Metadata Extraction
# =============================================================================


class TestMetadataExtraction:
    """Tests for metadata extraction."""

    def test_meta_description(self, parser: HTMLParser) -> None:
        """Meta description is extracted."""
        html = '<meta name="description" content="Page description">'
        result = parser.parse(html)
        assert result.metadata.get("description") == "Page description"

    def test_meta_keywords(self, parser: HTMLParser) -> None:
        """Meta keywords are extracted."""
        html = '<meta name="keywords" content="python, testing">'
        result = parser.parse(html)
        assert result.metadata.get("keywords") == "python, testing"

    def test_og_tags(self, parser: HTMLParser) -> None:
        """OpenGraph tags are extracted."""
        html = '<meta property="og:title" content="OG Title">'
        result = parser.parse(html)
        assert result.metadata.get("og:title") == "OG Title"

    def test_twitter_cards(self, parser: HTMLParser) -> None:
        """Twitter card tags are extracted."""
        html = '<meta name="twitter:card" content="summary">'
        result = parser.parse(html)
        assert result.metadata.get("twitter:card") == "summary"

    def test_missing_content_attribute(self, parser: HTMLParser) -> None:
        """Meta tags without content are handled."""
        html = '<meta name="author"><meta name="keywords" content="test">'
        result = parser.parse(html)
        assert "author" not in result.metadata
        assert result.metadata.get("keywords") == "test"


# =============================================================================
# Test Title Extraction
# =============================================================================


class TestTitleExtraction:
    """Tests for title extraction."""

    def test_simple_title(self, parser: HTMLParser) -> None:
        """Simple title is extracted."""
        html = "<title>Page Title</title>"
        result = parser.parse(html)
        assert result.title == "Page Title"

    def test_title_with_entities(self, parser: HTMLParser) -> None:
        """Title with HTML entities is extracted."""
        html = "<title>A &amp; B</title>"
        result = parser.parse(html)
        assert "A" in result.title
        assert "B" in result.title

    def test_empty_title(self, parser: HTMLParser) -> None:
        """Empty title is handled."""
        html = "<title></title>"
        result = parser.parse(html)
        # Empty title might be None or empty string
        assert result.title is None or result.title == ""

    def test_missing_title(self, parser: HTMLParser) -> None:
        """Missing title is handled."""
        html = "<p>No title here</p>"
        result = parser.parse(html)
        assert result.title is None

    def test_multiple_titles(self, parser: HTMLParser) -> None:
        """Multiple title tags - first is used."""
        html = "<title>First</title><title>Second</title>"
        result = parser.parse(html)
        assert result.title == "First"


# =============================================================================
# Test extract_main_content
# =============================================================================


class TestExtractMainContent:
    """Tests for main content extraction."""

    def test_finds_main_tag(self, parser: HTMLParser) -> None:
        """Finds content in <main> tag."""
        html = "<nav>Nav</nav><main>Main content</main><footer>Foot</footer>"
        result = parser.extract_main_content(html)
        assert "Main content" in result
        assert "Nav" not in result

    def test_finds_article_tag(self, parser: HTMLParser) -> None:
        """Finds content in <article> tag when no main."""
        html = "<nav>Nav</nav><article>Article content</article>"
        result = parser.extract_main_content(html)
        assert "Article content" in result

    def test_finds_content_class(self, parser: HTMLParser) -> None:
        """Finds div with content class."""
        html = '<nav>Nav</nav><div class="content">Main content</div>'
        result = parser.extract_main_content(html)
        assert "Main content" in result

    def test_falls_back_to_body(self, parser: HTMLParser) -> None:
        """Falls back to body if no main areas found."""
        html = "<body><div>Some content</div></body>"
        result = parser.extract_main_content(html)
        assert "Some content" in result
