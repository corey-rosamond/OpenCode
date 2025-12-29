"""Intent classification for natural language requests.

This module provides intent detection from user input, recognizing
patterns like "replace all X with Y" or "find files matching *.py".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class IntentType(str, Enum):
    """Types of user intents that can be classified."""

    # File operations
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"

    # Search operations
    FIND_FILES = "find_files"
    SEARCH_CONTENT = "search_content"
    FIND_DEFINITION = "find_definition"

    # Code modifications
    REPLACE_TEXT = "replace_text"
    REPLACE_ALL = "replace_all"
    RENAME_SYMBOL = "rename_symbol"
    REFACTOR = "refactor"

    # Execution
    RUN_COMMAND = "run_command"
    RUN_TESTS = "run_tests"
    BUILD_PROJECT = "build_project"

    # Information
    EXPLAIN_CODE = "explain_code"
    SHOW_STRUCTURE = "show_structure"

    # Web
    FETCH_URL = "fetch_url"
    SEARCH_WEB = "search_web"

    # Unknown/general
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """A classified intent from user input.

    Attributes:
        type: The classified intent type.
        confidence: Confidence score (0.0 to 1.0).
        parameters: Extracted parameters from the input.
        original_text: The original user input.
        matched_pattern: The pattern that matched (if any).
    """

    type: IntentType
    confidence: float
    parameters: dict[str, Any] = field(default_factory=dict)
    original_text: str = ""
    matched_pattern: str = ""

    def __post_init__(self) -> None:
        """Validate confidence is in range."""
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class IntentPattern:
    """A pattern for matching intents.

    Attributes:
        intent_type: The intent type this pattern matches.
        pattern: Regex pattern to match.
        confidence: Base confidence for this pattern.
        parameter_extractors: Named groups to extract as parameters.
        keywords: Keywords that boost confidence.
    """

    intent_type: IntentType
    pattern: str
    confidence: float = 0.8
    parameter_extractors: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


class IntentClassifier:
    """Classifies user intent from natural language input.

    Uses pattern matching and keyword detection to identify what
    the user wants to do and extract relevant parameters.
    """

    # Pattern library for intent classification
    PATTERNS: ClassVar[list[IntentPattern]] = [
        # Replace all patterns (highest priority for replace_all detection)
        IntentPattern(
            intent_type=IntentType.REPLACE_ALL,
            pattern=r"replace\s+(?:all|every|each)\s+(?:instances?\s+of\s+)?['\"]?(?P<old_text>[^'\"\s]+(?:\s+[^'\"\s]+)*?)['\"]?\s+(?:with|to|by)\s+['\"]?(?P<new_text>[^'\"\s]+(?:\s+[^'\"\s]+)*?)['\"]?(?:\s+in\s+(?P<file_path>\S+))?$",
            confidence=0.95,
            parameter_extractors=["old_text", "new_text", "file_path"],
            keywords=["replace", "all", "every", "each"],
        ),
        IntentPattern(
            intent_type=IntentType.REPLACE_ALL,
            pattern=r"replace\s+(?:all|every|each)\s+(?:instances?\s+of\s+)?'(?P<old_text>[^']+)'\s+(?:with|to|by)\s+'(?P<new_text>[^']+)'",
            confidence=0.95,
            parameter_extractors=["old_text", "new_text"],
            keywords=["replace", "all", "every", "each"],
        ),
        IntentPattern(
            intent_type=IntentType.REPLACE_ALL,
            pattern=r'replace\s+(?:all|every|each)\s+(?:instances?\s+of\s+)?"(?P<old_text>[^"]+)"\s+(?:with|to|by)\s+"(?P<new_text>[^"]+)"',
            confidence=0.95,
            parameter_extractors=["old_text", "new_text"],
            keywords=["replace", "all", "every", "each"],
        ),
        IntentPattern(
            intent_type=IntentType.REPLACE_ALL,
            pattern=r"change\s+(?:all|every|each)\s+'(?P<old_text>[^']+)'\s+(?:to|into)\s+'(?P<new_text>[^']+)'",
            confidence=0.9,
            parameter_extractors=["old_text", "new_text"],
            keywords=["change", "all", "every"],
        ),
        IntentPattern(
            intent_type=IntentType.REPLACE_ALL,
            pattern=r"change\s+(?:all|every|each)\s+(?P<old_text>\w+)\s+(?:to|into)\s+(?P<new_text>\w+)",
            confidence=0.9,
            parameter_extractors=["old_text", "new_text"],
            keywords=["change", "all", "every"],
        ),
        IntentPattern(
            intent_type=IntentType.REPLACE_ALL,
            pattern=r"change\s+(?:all\s+)?(?:occurrences?|instances?)\s+(?:of\s+)?(?P<old_text>\w+)\s+(?:to|with)\s+(?P<new_text>\w+)",
            confidence=0.9,
            parameter_extractors=["old_text", "new_text"],
            keywords=["change", "occurrences", "instances"],
        ),
        # Single replace patterns
        IntentPattern(
            intent_type=IntentType.REPLACE_TEXT,
            pattern=r"replace\s+'(?P<old_text>[^']+)'\s+(?:with|to|by)\s+'(?P<new_text>[^']+)'",
            confidence=0.9,
            parameter_extractors=["old_text", "new_text"],
            keywords=["replace"],
        ),
        IntentPattern(
            intent_type=IntentType.REPLACE_TEXT,
            pattern=r'replace\s+"(?P<old_text>[^"]+)"\s+(?:with|to|by)\s+"(?P<new_text>[^"]+)"',
            confidence=0.9,
            parameter_extractors=["old_text", "new_text"],
            keywords=["replace"],
        ),
        IntentPattern(
            intent_type=IntentType.REPLACE_TEXT,
            pattern=r"replace\s+(?P<old_text>\w+)\s+(?:with|to|by)\s+(?P<new_text>\w+)",
            confidence=0.85,
            parameter_extractors=["old_text", "new_text"],
            keywords=["replace"],
        ),
        # Rename patterns
        IntentPattern(
            intent_type=IntentType.RENAME_SYMBOL,
            pattern=r"rename\s+(?:the\s+)?(?:function|method|class|variable|const|let|var)?\s*['\"]?(?P<old_name>\w+)['\"]?\s+(?:to|as)\s+['\"]?(?P<new_name>\w+)['\"]?",
            confidence=0.9,
            parameter_extractors=["old_name", "new_name"],
            keywords=["rename"],
        ),
        IntentPattern(
            intent_type=IntentType.RENAME_SYMBOL,
            pattern=r"rename\s+['\"]?(?P<old_name>\w+)['\"]?\s+(?:to|as)\s+['\"]?(?P<new_name>\w+)['\"]?",
            confidence=0.85,
            parameter_extractors=["old_name", "new_name"],
            keywords=["rename"],
        ),
        # Find files patterns
        IntentPattern(
            intent_type=IntentType.FIND_FILES,
            pattern=r"(?:find|search\s+for|list|show)\s+(?:all\s+)?files?\s+(?:matching|like|named|with\s+pattern)\s+['\"]?(?P<pattern>\S+)['\"]?",
            confidence=0.9,
            parameter_extractors=["pattern"],
            keywords=["find", "files", "matching"],
        ),
        IntentPattern(
            intent_type=IntentType.FIND_FILES,
            pattern=r"(?:find|list|show)\s+(?:all\s+)?(?P<pattern>\*\.\w+)\s+files?",
            confidence=0.85,
            parameter_extractors=["pattern"],
            keywords=["find", "files"],
        ),
        # Find definition patterns (before search content to prioritize "defined")
        IntentPattern(
            intent_type=IntentType.FIND_DEFINITION,
            pattern=r"(?:find|show|go\s+to)\s+(?:the\s+)?definition\s+(?:of\s+)?['\"]?(?P<symbol>\w+)['\"]?",
            confidence=0.9,
            parameter_extractors=["symbol"],
            keywords=["definition", "find"],
        ),
        IntentPattern(
            intent_type=IntentType.FIND_DEFINITION,
            pattern=r"where\s+is\s+['\"]?(?P<symbol>\w+)['\"]?\s+defined",
            confidence=0.92,
            parameter_extractors=["symbol"],
            keywords=["where", "defined"],
        ),
        # Search content patterns
        IntentPattern(
            intent_type=IntentType.SEARCH_CONTENT,
            pattern=r"(?:search|grep|find)\s+(?:for\s+)?['\"]?(?P<query>[^'\"]+?)['\"]?\s+(?:in|across|within)\s+(?:the\s+)?(?:codebase|project|files?)",
            confidence=0.9,
            parameter_extractors=["query"],
            keywords=["search", "grep", "find", "codebase"],
        ),
        IntentPattern(
            intent_type=IntentType.SEARCH_CONTENT,
            pattern=r"where\s+(?:is|are|do(?:es)?)\s+['\"]?(?P<query>[^'\"]+?)['\"]?\s+(?:used|called|referenced)",
            confidence=0.85,
            parameter_extractors=["query"],
            keywords=["where", "used"],
        ),
        # Read file patterns
        IntentPattern(
            intent_type=IntentType.READ_FILE,
            pattern=r"(?:read|show|display|open|view|cat)\s+(?:the\s+)?(?:file\s+)?['\"]?(?P<file_path>\S+\.\w+)['\"]?",
            confidence=0.85,
            parameter_extractors=["file_path"],
            keywords=["read", "show", "open", "view"],
        ),
        IntentPattern(
            intent_type=IntentType.READ_FILE,
            pattern=r"(?:what(?:'s|\s+is)\s+in|show\s+me)\s+['\"]?(?P<file_path>\S+\.\w+)['\"]?",
            confidence=0.8,
            parameter_extractors=["file_path"],
            keywords=["what", "show"],
        ),
        # Create file patterns
        IntentPattern(
            intent_type=IntentType.CREATE_FILE,
            pattern=r"(?:create|make|add|new)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+|named\s+)?['\"]?(?P<file_path>\S+)['\"]?",
            confidence=0.9,
            parameter_extractors=["file_path"],
            keywords=["create", "make", "new", "file"],
        ),
        IntentPattern(
            intent_type=IntentType.CREATE_FILE,
            pattern=r"(?:add|create|make)\s+(?:a\s+)?(?:new\s+)?['\"]?(?P<file_path>\S+\.\w+)['\"]?\s+file",
            confidence=0.9,
            parameter_extractors=["file_path"],
            keywords=["add", "create", "new", "file"],
        ),
        # Write file patterns
        IntentPattern(
            intent_type=IntentType.WRITE_FILE,
            pattern=r"(?:write|save)\s+(?:to\s+)?(?:the\s+)?(?:file\s+)?['\"]?(?P<file_path>\S+)['\"]?",
            confidence=0.8,
            parameter_extractors=["file_path"],
            keywords=["write", "save"],
        ),
        # Edit file patterns
        IntentPattern(
            intent_type=IntentType.EDIT_FILE,
            pattern=r"(?:edit|modify|update|change)\s+(?:the\s+)?(?:file\s+)?['\"]?(?P<file_path>\S+\.\w+)['\"]?",
            confidence=0.8,
            parameter_extractors=["file_path"],
            keywords=["edit", "modify", "update"],
        ),
        # Delete file patterns
        IntentPattern(
            intent_type=IntentType.DELETE_FILE,
            pattern=r"(?:delete|remove|rm)\s+(?:the\s+)?(?:file\s+)?['\"]?(?P<file_path>\S+)['\"]?",
            confidence=0.85,
            parameter_extractors=["file_path"],
            keywords=["delete", "remove"],
        ),
        # Run command patterns
        IntentPattern(
            intent_type=IntentType.RUN_COMMAND,
            pattern=r"(?:run|execute|exec)\s+(?:the\s+)?(?:command\s+)?['\"]?(?P<command>.+)['\"]?",
            confidence=0.85,
            parameter_extractors=["command"],
            keywords=["run", "execute"],
        ),
        # Run tests patterns
        IntentPattern(
            intent_type=IntentType.RUN_TESTS,
            pattern=r"(?:run|execute)\s+(?:the\s+)?tests?(?:\s+for\s+(?P<target>\S+))?",
            confidence=0.9,
            parameter_extractors=["target"],
            keywords=["run", "test", "tests"],
        ),
        IntentPattern(
            intent_type=IntentType.RUN_TESTS,
            pattern=r"test\s+(?:the\s+)?(?P<target>\S+)?",
            confidence=0.8,
            parameter_extractors=["target"],
            keywords=["test"],
        ),
        # Build patterns
        IntentPattern(
            intent_type=IntentType.BUILD_PROJECT,
            pattern=r"(?:build|compile)\s+(?:the\s+)?(?:project|app|application)?",
            confidence=0.85,
            parameter_extractors=[],
            keywords=["build", "compile"],
        ),
        # Explain patterns
        IntentPattern(
            intent_type=IntentType.EXPLAIN_CODE,
            pattern=r"(?:explain|describe|what\s+does)\s+(?:the\s+)?(?:code\s+in\s+)?['\"]?(?P<target>\S+)['\"]?",
            confidence=0.8,
            parameter_extractors=["target"],
            keywords=["explain", "describe", "what"],
        ),
        # Refactor patterns
        IntentPattern(
            intent_type=IntentType.REFACTOR,
            pattern=r"refactor\s+(?:the\s+)?(?P<target>\S+)",
            confidence=0.85,
            parameter_extractors=["target"],
            keywords=["refactor"],
        ),
        # Fetch URL patterns
        IntentPattern(
            intent_type=IntentType.FETCH_URL,
            pattern=r"(?:fetch|get|download)\s+(?:from\s+)?(?P<url>https?://\S+)",
            confidence=0.9,
            parameter_extractors=["url"],
            keywords=["fetch", "url", "http"],
        ),
        # Web search patterns
        IntentPattern(
            intent_type=IntentType.SEARCH_WEB,
            pattern=r"(?:search\s+(?:the\s+)?web|google|look\s+up)\s+(?:for\s+)?['\"]?(?P<query>.+)['\"]?",
            confidence=0.85,
            parameter_extractors=["query"],
            keywords=["search", "web", "google"],
        ),
        # Show structure patterns
        IntentPattern(
            intent_type=IntentType.SHOW_STRUCTURE,
            pattern=r"(?:show|display)\s+(?:the\s+)?(?:project\s+)?(?:structure|tree|layout)",
            confidence=0.85,
            parameter_extractors=[],
            keywords=["structure", "tree", "layout"],
        ),
    ]

    # Keyword to intent type mapping for fallback classification
    KEYWORD_INTENTS: ClassVar[dict[str, IntentType]] = {
        "replace": IntentType.REPLACE_TEXT,
        "rename": IntentType.RENAME_SYMBOL,
        "find": IntentType.FIND_FILES,
        "search": IntentType.SEARCH_CONTENT,
        "grep": IntentType.SEARCH_CONTENT,
        "read": IntentType.READ_FILE,
        "show": IntentType.READ_FILE,
        "open": IntentType.READ_FILE,
        "create": IntentType.CREATE_FILE,
        "write": IntentType.WRITE_FILE,
        "edit": IntentType.EDIT_FILE,
        "modify": IntentType.EDIT_FILE,
        "delete": IntentType.DELETE_FILE,
        "remove": IntentType.DELETE_FILE,
        "run": IntentType.RUN_COMMAND,
        "execute": IntentType.RUN_COMMAND,
        "test": IntentType.RUN_TESTS,
        "build": IntentType.BUILD_PROJECT,
        "compile": IntentType.BUILD_PROJECT,
        "explain": IntentType.EXPLAIN_CODE,
        "refactor": IntentType.REFACTOR,
        "fetch": IntentType.FETCH_URL,
    }

    def __init__(self) -> None:
        """Initialize the intent classifier."""
        self._compiled_patterns: list[tuple[IntentPattern, re.Pattern[str]]] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        for pattern in self.PATTERNS:
            try:
                compiled = re.compile(pattern.pattern, re.IGNORECASE)
                self._compiled_patterns.append((pattern, compiled))
            except re.error:
                # Skip invalid patterns
                pass

    def classify(self, text: str) -> Intent:
        """Classify user intent from text.

        Args:
            text: User input text.

        Returns:
            Classified Intent with type, confidence, and parameters.
        """
        text = text.strip()
        if not text:
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                original_text=text,
            )

        # Try pattern matching first
        best_intent = self._match_patterns(text)

        # If no pattern matched well, try keyword fallback
        if best_intent.confidence < 0.5:
            keyword_intent = self._keyword_fallback(text)
            if keyword_intent.confidence > best_intent.confidence:
                best_intent = keyword_intent

        return best_intent

    def classify_multiple(self, text: str, top_k: int = 3) -> list[Intent]:
        """Get multiple possible intents ranked by confidence.

        Args:
            text: User input text.
            top_k: Maximum number of intents to return.

        Returns:
            List of possible intents, sorted by confidence.
        """
        text = text.strip()
        if not text:
            return [Intent(type=IntentType.UNKNOWN, confidence=0.0, original_text=text)]

        intents: list[Intent] = []

        # Collect all matching intents
        for pattern_info, compiled in self._compiled_patterns:
            match = compiled.search(text)
            if match:
                parameters = self._extract_parameters(match, pattern_info)
                confidence = self._calculate_confidence(text, pattern_info, match)
                intents.append(Intent(
                    type=pattern_info.intent_type,
                    confidence=confidence,
                    parameters=parameters,
                    original_text=text,
                    matched_pattern=pattern_info.pattern,
                ))

        # Add keyword fallback if needed
        if len(intents) < top_k:
            keyword_intent = self._keyword_fallback(text)
            if keyword_intent.type != IntentType.UNKNOWN:
                intents.append(keyword_intent)

        # Sort by confidence and deduplicate by type
        seen_types: set[IntentType] = set()
        unique_intents: list[Intent] = []
        for intent in sorted(intents, key=lambda i: i.confidence, reverse=True):
            if intent.type not in seen_types:
                seen_types.add(intent.type)
                unique_intents.append(intent)
            if len(unique_intents) >= top_k:
                break

        if not unique_intents:
            unique_intents.append(Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                original_text=text,
            ))

        return unique_intents

    def _match_patterns(self, text: str) -> Intent:
        """Match text against patterns.

        Args:
            text: Input text.

        Returns:
            Best matching intent.
        """
        best_intent = Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            original_text=text,
        )

        for pattern_info, compiled in self._compiled_patterns:
            match = compiled.search(text)
            if match:
                confidence = self._calculate_confidence(text, pattern_info, match)
                if confidence > best_intent.confidence:
                    parameters = self._extract_parameters(match, pattern_info)
                    best_intent = Intent(
                        type=pattern_info.intent_type,
                        confidence=confidence,
                        parameters=parameters,
                        original_text=text,
                        matched_pattern=pattern_info.pattern,
                    )

        return best_intent

    def _extract_parameters(
        self,
        match: re.Match[str],
        pattern_info: IntentPattern,
    ) -> dict[str, Any]:
        """Extract parameters from regex match.

        Args:
            match: Regex match object.
            pattern_info: Pattern that matched.

        Returns:
            Extracted parameters dictionary.
        """
        parameters: dict[str, Any] = {}

        for extractor in pattern_info.parameter_extractors:
            try:
                value = match.group(extractor)
                if value:
                    # Clean up the value
                    value = value.strip().strip("'\"")
                    parameters[extractor] = value
            except IndexError:
                pass

        return parameters

    def _calculate_confidence(
        self,
        text: str,
        pattern_info: IntentPattern,
        match: re.Match[str],
    ) -> float:
        """Calculate confidence score for a match.

        Args:
            text: Original input text.
            pattern_info: Pattern that matched.
            match: Regex match object.

        Returns:
            Confidence score (0.0 to 1.0).
        """
        confidence = pattern_info.confidence

        # Boost confidence for keyword matches
        text_lower = text.lower()
        keyword_matches = sum(1 for kw in pattern_info.keywords if kw in text_lower)
        if keyword_matches > 0:
            confidence = min(1.0, confidence + (keyword_matches * 0.02))

        # Boost for match coverage (how much of the text was matched)
        match_ratio = len(match.group(0)) / len(text)
        if match_ratio > 0.5:
            confidence = min(1.0, confidence + 0.05)

        return confidence

    def _keyword_fallback(self, text: str) -> Intent:
        """Fallback classification using keyword matching.

        Args:
            text: Input text.

        Returns:
            Intent based on keyword matching.
        """
        text_lower = text.lower()
        words = set(re.findall(r'\w+', text_lower))

        best_type = IntentType.UNKNOWN
        best_confidence = 0.0

        for keyword, intent_type in self.KEYWORD_INTENTS.items():
            if keyword in words:
                # Base confidence for keyword match
                confidence = 0.5

                # Boost if keyword is at the start
                if text_lower.startswith(keyword):
                    confidence = 0.65

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_type = intent_type

        return Intent(
            type=best_type,
            confidence=best_confidence,
            original_text=text,
        )

    def has_replace_all_intent(self, text: str) -> bool:
        """Check if text indicates a replace-all intent.

        This is a quick check for the common case of needing
        to set replace_all=true on the Edit tool.

        Args:
            text: User input text.

        Returns:
            True if replace-all intent is detected.
        """
        text_lower = text.lower()

        # Check for explicit "all" keywords
        replace_all_patterns = [
            r"replace\s+all",
            r"replace\s+every",
            r"replace\s+each",
            r"change\s+all",
            r"change\s+every",
            r"rename\s+all",
            r"update\s+all",
            r"all\s+instances",
            r"every\s+instance",
            r"everywhere",
            r"throughout",
            r"globally",
        ]

        for pattern in replace_all_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def extract_replacement_pair(self, text: str) -> tuple[str, str] | None:
        """Extract old/new text pair from replacement request.

        Args:
            text: User input text.

        Returns:
            Tuple of (old_text, new_text) or None if not found.
        """
        intent = self.classify(text)

        if intent.type in (IntentType.REPLACE_TEXT, IntentType.REPLACE_ALL):
            old_text = intent.parameters.get("old_text")
            new_text = intent.parameters.get("new_text")
            if old_text and new_text:
                return (old_text, new_text)

        if intent.type == IntentType.RENAME_SYMBOL:
            old_name = intent.parameters.get("old_name")
            new_name = intent.parameters.get("new_name")
            if old_name and new_name:
                return (old_name, new_name)

        return None
