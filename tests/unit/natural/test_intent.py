"""Tests for intent classification."""

from __future__ import annotations

import pytest

from code_forge.natural.intent import (
    Intent,
    IntentClassifier,
    IntentPattern,
    IntentType,
)


class TestIntentType:
    """Tests for IntentType enum."""

    def test_file_operations(self) -> None:
        """Test file operation types exist."""
        assert IntentType.READ_FILE.value == "read_file"
        assert IntentType.WRITE_FILE.value == "write_file"
        assert IntentType.EDIT_FILE.value == "edit_file"

    def test_search_operations(self) -> None:
        """Test search operation types exist."""
        assert IntentType.FIND_FILES.value == "find_files"
        assert IntentType.SEARCH_CONTENT.value == "search_content"

    def test_replace_operations(self) -> None:
        """Test replace operation types exist."""
        assert IntentType.REPLACE_TEXT.value == "replace_text"
        assert IntentType.REPLACE_ALL.value == "replace_all"


class TestIntent:
    """Tests for Intent dataclass."""

    def test_creation(self) -> None:
        """Test intent creation."""
        intent = Intent(
            type=IntentType.READ_FILE,
            confidence=0.9,
            parameters={"file_path": "test.py"},
        )
        assert intent.type == IntentType.READ_FILE
        assert intent.confidence == 0.9
        assert intent.parameters["file_path"] == "test.py"

    def test_confidence_clamping(self) -> None:
        """Test confidence is clamped to 0-1 range."""
        intent = Intent(type=IntentType.UNKNOWN, confidence=1.5)
        assert intent.confidence == 1.0

        intent = Intent(type=IntentType.UNKNOWN, confidence=-0.5)
        assert intent.confidence == 0.0


class TestIntentClassifier:
    """Tests for IntentClassifier."""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        """Create a classifier instance."""
        return IntentClassifier()

    def test_empty_input(self, classifier: IntentClassifier) -> None:
        """Test handling of empty input."""
        intent = classifier.classify("")
        assert intent.type == IntentType.UNKNOWN
        assert intent.confidence == 0.0

    def test_replace_all_detection(self, classifier: IntentClassifier) -> None:
        """Test replace all intent detection."""
        texts = [
            "replace all foo with bar",
            "Replace every instance of foo with bar",
            "change all occurrences of foo to bar",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.REPLACE_ALL, f"Failed for: {text}"
            assert intent.confidence >= 0.8

    def test_replace_all_parameters(self, classifier: IntentClassifier) -> None:
        """Test parameter extraction from replace all."""
        intent = classifier.classify("replace all 'oldValue' with 'newValue'")
        assert intent.type == IntentType.REPLACE_ALL
        assert intent.parameters.get("old_text") == "oldValue"
        assert intent.parameters.get("new_text") == "newValue"

    def test_simple_replace_detection(self, classifier: IntentClassifier) -> None:
        """Test simple replace intent detection."""
        intent = classifier.classify("replace foo with bar")
        assert intent.type == IntentType.REPLACE_TEXT
        assert intent.parameters.get("old_text") == "foo"
        assert intent.parameters.get("new_text") == "bar"

    def test_rename_detection(self, classifier: IntentClassifier) -> None:
        """Test rename intent detection."""
        texts = [
            "rename function getData to fetchData",
            "rename oldName to newName",
            "rename the class User to Person",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.RENAME_SYMBOL, f"Failed for: {text}"
            assert intent.confidence >= 0.8

    def test_rename_parameters(self, classifier: IntentClassifier) -> None:
        """Test parameter extraction from rename."""
        intent = classifier.classify("rename myFunc to betterFunc")
        assert intent.type == IntentType.RENAME_SYMBOL
        assert intent.parameters.get("old_name") == "myFunc"
        assert intent.parameters.get("new_name") == "betterFunc"

    def test_find_files_detection(self, classifier: IntentClassifier) -> None:
        """Test find files intent detection."""
        texts = [
            "find all files matching *.py",
            "find files named config.json",
            "list all *.ts files",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.FIND_FILES, f"Failed for: {text}"

    def test_find_files_pattern(self, classifier: IntentClassifier) -> None:
        """Test pattern extraction from find files."""
        intent = classifier.classify("find files matching *.py")
        assert intent.type == IntentType.FIND_FILES
        assert "pattern" in intent.parameters

    def test_search_content_detection(self, classifier: IntentClassifier) -> None:
        """Test search content intent detection."""
        texts = [
            "search for 'TODO' in the codebase",
            "grep for error in files",
            "where is handleError used",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.SEARCH_CONTENT, f"Failed for: {text}"

    def test_read_file_detection(self, classifier: IntentClassifier) -> None:
        """Test read file intent detection."""
        texts = [
            "read config.py",
            "show main.js",
            "open test.ts",
            "view package.json",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.READ_FILE, f"Failed for: {text}"

    def test_read_file_path(self, classifier: IntentClassifier) -> None:
        """Test file path extraction from read."""
        intent = classifier.classify("read src/main.py")
        assert intent.type == IntentType.READ_FILE
        assert intent.parameters.get("file_path") == "src/main.py"

    def test_create_file_detection(self, classifier: IntentClassifier) -> None:
        """Test create file intent detection."""
        texts = [
            "create a new file called test.py",
            "make a file named config.json",
            "add new utils.ts file",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.CREATE_FILE, f"Failed for: {text}"

    def test_run_tests_detection(self, classifier: IntentClassifier) -> None:
        """Test run tests intent detection."""
        texts = [
            "run the tests",
            "execute tests for utils",
            "run tests",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.RUN_TESTS, f"Failed for: {text}"

    def test_build_project_detection(self, classifier: IntentClassifier) -> None:
        """Test build project intent detection."""
        texts = [
            "build the project",
            "compile the app",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.BUILD_PROJECT, f"Failed for: {text}"

    def test_fetch_url_detection(self, classifier: IntentClassifier) -> None:
        """Test fetch URL intent detection."""
        intent = classifier.classify("fetch https://api.example.com/data")
        assert intent.type == IntentType.FETCH_URL
        assert intent.parameters.get("url") == "https://api.example.com/data"

    def test_classify_multiple(self, classifier: IntentClassifier) -> None:
        """Test getting multiple possible intents."""
        intents = classifier.classify_multiple("find and edit config.py", top_k=3)
        assert len(intents) >= 1
        assert len(intents) <= 3
        # Should be sorted by confidence
        for i in range(len(intents) - 1):
            assert intents[i].confidence >= intents[i + 1].confidence

    def test_has_replace_all_intent(self, classifier: IntentClassifier) -> None:
        """Test replace all intent detection helper."""
        assert classifier.has_replace_all_intent("replace all foo with bar")
        assert classifier.has_replace_all_intent("change every instance of x to y")
        assert classifier.has_replace_all_intent("update foo everywhere")
        assert classifier.has_replace_all_intent("rename all occurrences globally")
        assert not classifier.has_replace_all_intent("replace foo with bar")
        assert not classifier.has_replace_all_intent("edit the file")

    def test_extract_replacement_pair(self, classifier: IntentClassifier) -> None:
        """Test extraction of replacement pairs."""
        pair = classifier.extract_replacement_pair("replace oldValue with newValue")
        assert pair == ("oldValue", "newValue")

        pair = classifier.extract_replacement_pair("rename getData to fetchData")
        assert pair == ("getData", "fetchData")

        pair = classifier.extract_replacement_pair("read the file")
        assert pair is None

    def test_keyword_fallback(self, classifier: IntentClassifier) -> None:
        """Test keyword-based fallback classification."""
        # Test that keywords trigger fallback
        intent = classifier.classify("just search something")
        assert intent.type == IntentType.SEARCH_CONTENT or intent.confidence > 0

    def test_confidence_boost_for_keywords(self, classifier: IntentClassifier) -> None:
        """Test that keyword matches boost confidence."""
        intent1 = classifier.classify("replace all x with y in file")
        intent2 = classifier.classify("x y z")

        # The one with clear keywords should have higher confidence
        assert intent1.confidence > intent2.confidence

    def test_find_definition_detection(self, classifier: IntentClassifier) -> None:
        """Test find definition intent detection."""
        texts = [
            "find the definition of handleError",
            "show definition of MyClass",
            "where is processData defined",
        ]
        for text in texts:
            intent = classifier.classify(text)
            assert intent.type == IntentType.FIND_DEFINITION, f"Failed for: {text}"

    def test_refactor_detection(self, classifier: IntentClassifier) -> None:
        """Test refactor intent detection."""
        intent = classifier.classify("refactor the utils module")
        assert intent.type == IntentType.REFACTOR


class TestIntentPattern:
    """Tests for IntentPattern dataclass."""

    def test_creation(self) -> None:
        """Test pattern creation."""
        pattern = IntentPattern(
            intent_type=IntentType.REPLACE_ALL,
            pattern=r"replace all",
            confidence=0.9,
            keywords=["replace", "all"],
        )
        assert pattern.intent_type == IntentType.REPLACE_ALL
        assert pattern.confidence == 0.9
        assert "replace" in pattern.keywords

    def test_default_values(self) -> None:
        """Test default values."""
        pattern = IntentPattern(
            intent_type=IntentType.READ_FILE,
            pattern=r"read",
        )
        assert pattern.confidence == 0.8
        assert pattern.parameter_extractors == []
        assert pattern.keywords == []
