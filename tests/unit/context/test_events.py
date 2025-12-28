"""Unit tests for context compression events."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from code_forge.context.events import (
    CompressionEvent,
    CompressionEventType,
    CompressionObserver,
    WarningLevel,
    get_warning_level,
)


class TestCompressionEventType:
    """Tests for CompressionEventType enum."""

    def test_values(self) -> None:
        """Should have expected values."""
        assert CompressionEventType.TRUNCATION.value == "truncation"
        assert CompressionEventType.COMPACTION.value == "compaction"
        assert CompressionEventType.WARNING.value == "warning"
        assert CompressionEventType.CLEARED.value == "cleared"


class TestWarningLevel:
    """Tests for WarningLevel enum."""

    def test_values(self) -> None:
        """Should have expected values."""
        assert WarningLevel.NONE.value == "none"
        assert WarningLevel.CAUTION.value == "caution"
        assert WarningLevel.CRITICAL.value == "critical"


class TestCompressionEvent:
    """Tests for CompressionEvent dataclass."""

    def test_create_truncation_event(self) -> None:
        """Should create truncation event with correct properties."""
        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
            usage_percentage=50.0,
            strategy="smart",
        )

        assert event.event_type == CompressionEventType.TRUNCATION
        assert event.tokens_before == 10000
        assert event.tokens_after == 5000
        assert event.messages_before == 20
        assert event.messages_after == 10
        assert event.usage_percentage == 50.0
        assert event.strategy == "smart"
        assert event.warning_level == WarningLevel.NONE

    def test_create_warning_event(self) -> None:
        """Should create warning event with warning level."""
        event = CompressionEvent(
            event_type=CompressionEventType.WARNING,
            tokens_before=8000,
            tokens_after=8000,
            messages_before=15,
            messages_after=15,
            warning_level=WarningLevel.CAUTION,
            usage_percentage=80.0,
        )

        assert event.event_type == CompressionEventType.WARNING
        assert event.warning_level == WarningLevel.CAUTION
        assert event.usage_percentage == 80.0

    def test_tokens_saved_property(self) -> None:
        """Should calculate tokens saved correctly."""
        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
        )

        assert event.tokens_saved == 5000

    def test_tokens_saved_no_negative(self) -> None:
        """Should not return negative tokens saved."""
        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=5000,
            tokens_after=10000,  # More after (edge case)
            messages_before=10,
            messages_after=20,
        )

        assert event.tokens_saved == 0

    def test_messages_removed_property(self) -> None:
        """Should calculate messages removed correctly."""
        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
        )

        assert event.messages_removed == 10

    def test_messages_removed_no_negative(self) -> None:
        """Should not return negative messages removed."""
        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=10,
            messages_after=20,  # More after (edge case)
        )

        assert event.messages_removed == 0

    def test_compression_ratio_property(self) -> None:
        """Should calculate compression ratio correctly."""
        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
        )

        assert event.compression_ratio == 0.5

    def test_compression_ratio_zero_before(self) -> None:
        """Should return 1.0 when tokens_before is 0."""
        event = CompressionEvent(
            event_type=CompressionEventType.CLEARED,
            tokens_before=0,
            tokens_after=0,
            messages_before=0,
            messages_after=0,
        )

        assert event.compression_ratio == 1.0

    def test_frozen_dataclass(self) -> None:
        """Should be immutable."""
        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            event.tokens_before = 999  # type: ignore


class TestGetWarningLevel:
    """Tests for get_warning_level function."""

    def test_none_level_below_80(self) -> None:
        """Should return NONE when below 80%."""
        assert get_warning_level(0) == WarningLevel.NONE
        assert get_warning_level(50) == WarningLevel.NONE
        assert get_warning_level(79.9) == WarningLevel.NONE

    def test_caution_level_80_to_90(self) -> None:
        """Should return CAUTION between 80% and 90%."""
        assert get_warning_level(80) == WarningLevel.CAUTION
        assert get_warning_level(85) == WarningLevel.CAUTION
        assert get_warning_level(89.9) == WarningLevel.CAUTION

    def test_critical_level_90_plus(self) -> None:
        """Should return CRITICAL at 90% and above."""
        assert get_warning_level(90) == WarningLevel.CRITICAL
        assert get_warning_level(95) == WarningLevel.CRITICAL
        assert get_warning_level(100) == WarningLevel.CRITICAL

    def test_custom_thresholds(self) -> None:
        """Should respect custom thresholds."""
        # Custom: warn at 70%, critical at 85%
        assert get_warning_level(60, warning_threshold=70, critical_threshold=85) == WarningLevel.NONE
        assert get_warning_level(75, warning_threshold=70, critical_threshold=85) == WarningLevel.CAUTION
        assert get_warning_level(85, warning_threshold=70, critical_threshold=85) == WarningLevel.CRITICAL
        assert get_warning_level(95, warning_threshold=70, critical_threshold=85) == WarningLevel.CRITICAL


class MockObserver:
    """Mock observer for testing."""

    def __init__(self) -> None:
        self.events: list[CompressionEvent] = []

    def on_compression_event(self, event: CompressionEvent) -> None:
        """Record the event."""
        self.events.append(event)


class TestCompressionObserver:
    """Tests for CompressionObserver protocol."""

    def test_observer_receives_events(self) -> None:
        """Should receive events when notified."""
        observer = MockObserver()
        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
        )

        observer.on_compression_event(event)

        assert len(observer.events) == 1
        assert observer.events[0] == event
