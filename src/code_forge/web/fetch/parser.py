"""HTML parser and converter."""

import logging
import re
from urllib.parse import urljoin

import html2text
from bs4 import BeautifulSoup

from ..types import ParsedContent

logger = logging.getLogger(__name__)


class HTMLParser:
    """Parses and converts HTML content."""

    def __init__(self) -> None:
        """Initialize parser."""
        self._h2t = html2text.HTML2Text()
        self._h2t.ignore_links = False
        self._h2t.ignore_images = False
        self._h2t.body_width = 0  # Don't wrap lines

    def parse(
        self,
        html: str,
        base_url: str | None = None,
    ) -> ParsedContent:
        """Parse HTML to structured content.

        Args:
            html: HTML content
            base_url: Base URL for relative links

        Returns:
            ParsedContent with extracted data
        """
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title: str | None = None
        if soup.title and soup.title.string:
            title = soup.title.string

        # Extract metadata
        metadata: dict[str, str] = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if name and content:
                metadata[str(name)] = str(content)

        # Extract links
        links: list[dict[str, str]] = []
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if base_url:
                href = urljoin(base_url, href)
            links.append({
                "text": a.get_text(strip=True),
                "url": href,
            })

        # Extract images
        images: list[dict[str, str]] = []
        for img in soup.find_all("img", src=True):
            src = str(img["src"])
            if base_url:
                src = urljoin(base_url, src)
            images.append({
                "alt": img.get("alt", ""),
                "src": src,
            })

        # Convert to text and markdown
        text = self.to_text(html)
        markdown = self.to_markdown(html)

        return ParsedContent(
            title=title,
            text=text,
            markdown=markdown,
            links=links,
            images=images,
            metadata=metadata,
        )

    def to_text(self, html: str) -> str:
        """Convert HTML to plain text.

        Args:
            html: HTML content

        Returns:
            Plain text content
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style
        for element in soup(["script", "style", "nav", "footer", "aside"]):
            element.decompose()

        text = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(line for line in lines if line)

        # Collapse multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown.

        Args:
            html: HTML content

        Returns:
            Markdown content
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "aside"]):
            element.decompose()

        # Convert using html2text
        markdown = self._h2t.handle(str(soup))

        # Clean up
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        return markdown.strip()

    # Attributes that can execute JavaScript (XSS vectors)
    DANGEROUS_ATTRS = frozenset([
        # Event handlers
        "onabort", "onafterprint", "onbeforeprint", "onbeforeunload", "onblur",
        "oncanplay", "oncanplaythrough", "onchange", "onclick", "oncontextmenu",
        "oncopy", "oncuechange", "oncut", "ondblclick", "ondrag", "ondragend",
        "ondragenter", "ondragleave", "ondragover", "ondragstart", "ondrop",
        "ondurationchange", "onemptied", "onended", "onerror", "onfocus",
        "onhashchange", "oninput", "oninvalid", "onkeydown", "onkeypress",
        "onkeyup", "onload", "onloadeddata", "onloadedmetadata", "onloadstart",
        "onmessage", "onmousedown", "onmousemove", "onmouseout", "onmouseover",
        "onmouseup", "onmousewheel", "onoffline", "ononline", "onpagehide",
        "onpageshow", "onpaste", "onpause", "onplay", "onplaying", "onpopstate",
        "onprogress", "onratechange", "onreset", "onresize", "onscroll",
        "onsearch", "onseeked", "onseeking", "onselect", "onstalled", "onstorage",
        "onsubmit", "onsuspend", "ontimeupdate", "ontoggle", "onunload",
        "onvolumechange", "onwaiting", "onwheel",
        # JavaScript URL handlers
        "href", "src", "action", "formaction", "data",  # Only dangerous with javascript: URLs
    ])

    def _sanitize_element(self, element: Any) -> None:
        """Remove dangerous attributes from an element.

        Args:
            element: BeautifulSoup element to sanitize
        """
        if not hasattr(element, "attrs"):
            return

        # Remove event handler attributes
        attrs_to_remove = []
        for attr in element.attrs:
            attr_lower = attr.lower()
            # Remove all event handlers (on*)
            if attr_lower.startswith("on"):
                attrs_to_remove.append(attr)
            # Remove javascript: URLs
            elif attr_lower in ("href", "src", "action", "formaction", "data"):
                value = element.get(attr, "")
                if isinstance(value, str) and value.strip().lower().startswith("javascript:"):
                    attrs_to_remove.append(attr)

        for attr in attrs_to_remove:
            del element[attr]

    def extract_main_content(self, html: str) -> str:
        """Extract main content, removing boilerplate and XSS vectors.

        Args:
            html: HTML content

        Returns:
            Sanitized main content HTML
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for element in soup([
            "script", "style", "nav", "header", "footer",
            "aside", "form", "iframe", "noscript",
        ]):
            element.decompose()

        # Sanitize all remaining elements (remove event handlers, javascript: URLs)
        for element in soup.find_all(True):  # True matches all tags
            self._sanitize_element(element)

        # Try to find main content area
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"class": re.compile(r"content|main|article")})
            or soup.find("div", {"id": re.compile(r"content|main|article")})
            or soup.body
            or soup
        )

        return str(main)
