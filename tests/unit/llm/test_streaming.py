"""Unit tests for StreamCollector."""

import pytest

from code_forge.llm.models import MessageRole, StreamChunk, TokenUsage
from code_forge.llm.streaming import StreamCollector


class TestStreamCollector:
    """Tests for StreamCollector class."""

    def test_initial_state(self) -> None:
        collector = StreamCollector()
        assert collector.content == ""
        assert collector.tool_calls == []
        assert collector.usage is None
        assert collector.model == ""
        assert collector.finish_reason is None
        assert not collector.is_complete

    def test_add_chunk_with_content(self) -> None:
        collector = StreamCollector()
        chunk_data = {
            "id": "gen-1",
            "model": "test/model",
            "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
        }
        chunk = StreamChunk.from_dict(chunk_data)
        result = collector.add_chunk(chunk)

        assert result == "Hello"
        assert collector.content == "Hello"
        assert collector.model == "test/model"

    def test_accumulate_content(self) -> None:
        collector = StreamCollector()
        chunks_data = [
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}]},
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"content": " "}, "finish_reason": None}]},
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"content": "World"}, "finish_reason": None}]},
        ]

        for chunk_data in chunks_data:
            chunk = StreamChunk.from_dict(chunk_data)
            collector.add_chunk(chunk)

        assert collector.content == "Hello World"

    def test_add_chunk_returns_new_content(self) -> None:
        collector = StreamCollector()
        chunks_data = [
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"content": "A"}, "finish_reason": None}]},
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"content": "B"}, "finish_reason": None}]},
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"content": "C"}, "finish_reason": None}]},
        ]

        results = []
        for chunk_data in chunks_data:
            chunk = StreamChunk.from_dict(chunk_data)
            result = collector.add_chunk(chunk)
            results.append(result)

        assert results == ["A", "B", "C"]

    def test_add_chunk_returns_none_for_no_content(self) -> None:
        collector = StreamCollector()
        chunk_data = {
            "id": "gen-1",
            "model": "test",
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
        chunk = StreamChunk.from_dict(chunk_data)
        result = collector.add_chunk(chunk)
        assert result is None

    def test_finish_reason_detection(self) -> None:
        collector = StreamCollector()
        chunks_data = [
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"content": "Hi"}, "finish_reason": None}]},
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]

        assert not collector.is_complete
        for chunk_data in chunks_data:
            chunk = StreamChunk.from_dict(chunk_data)
            collector.add_chunk(chunk)

        assert collector.is_complete
        assert collector.finish_reason == "stop"

    def test_usage_tracking(self) -> None:
        collector = StreamCollector()
        chunk_data = {
            "id": "gen-1",
            "model": "test",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        chunk = StreamChunk.from_dict(chunk_data)
        collector.add_chunk(chunk)

        assert isinstance(collector.usage, TokenUsage)
        assert collector.usage.prompt_tokens == 10
        assert collector.usage.completion_tokens == 5
        assert collector.usage.total_tokens == 15

    def test_get_message_with_content(self) -> None:
        collector = StreamCollector()
        chunks_data = [
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]},
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {"content": "Hello World"}, "finish_reason": None}]},
            {"id": "gen-1", "model": "test", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]

        for chunk_data in chunks_data:
            chunk = StreamChunk.from_dict(chunk_data)
            collector.add_chunk(chunk)

        message = collector.get_message()
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Hello World"
        assert message.tool_calls is None

    def test_get_message_empty_content(self) -> None:
        collector = StreamCollector()
        chunk_data = {
            "id": "gen-1",
            "model": "test",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        chunk = StreamChunk.from_dict(chunk_data)
        collector.add_chunk(chunk)

        message = collector.get_message()
        assert message.role == MessageRole.ASSISTANT
        assert message.content is None

    def test_tool_call_collection(self) -> None:
        collector = StreamCollector()
        chunks_data = [
            {
                "id": "gen-1",
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "read_file", "arguments": ""},
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "gen-1",
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"path"'}}]},
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "gen-1",
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"tool_calls": [{"index": 0, "function": {"arguments": ': "/tmp"}'}}]},
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "gen-1",
                "model": "test",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
            },
        ]

        for chunk_data in chunks_data:
            chunk = StreamChunk.from_dict(chunk_data)
            collector.add_chunk(chunk)

        assert len(collector.tool_calls) == 1
        assert collector.tool_calls[0]["id"] == "call_1"
        assert collector.tool_calls[0]["function"]["name"] == "read_file"
        assert collector.tool_calls[0]["function"]["arguments"] == '{"path": "/tmp"}'

    def test_get_message_with_tool_calls(self) -> None:
        collector = StreamCollector()
        chunks_data = [
            {
                "id": "gen-1",
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_abc",
                                    "type": "function",
                                    "function": {"name": "test_func", "arguments": "{}"},
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "gen-1",
                "model": "test",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
            },
        ]

        for chunk_data in chunks_data:
            chunk = StreamChunk.from_dict(chunk_data)
            collector.add_chunk(chunk)

        message = collector.get_message()
        assert message.role == MessageRole.ASSISTANT
        assert message.content is None
        assert isinstance(message.tool_calls, list)
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0].id == "call_abc"
        assert message.tool_calls[0].function["name"] == "test_func"

    def test_multiple_tool_calls(self) -> None:
        collector = StreamCollector()
        chunks_data = [
            {
                "id": "gen-1",
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "func1", "arguments": "{}"},
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "gen-1",
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 1,
                                    "id": "call_2",
                                    "type": "function",
                                    "function": {"name": "func2", "arguments": "{}"},
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "gen-1",
                "model": "test",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
            },
        ]

        for chunk_data in chunks_data:
            chunk = StreamChunk.from_dict(chunk_data)
            collector.add_chunk(chunk)

        assert len(collector.tool_calls) == 2
        assert collector.tool_calls[0]["id"] == "call_1"
        assert collector.tool_calls[1]["id"] == "call_2"

    def test_model_updated_from_chunks(self) -> None:
        collector = StreamCollector()
        chunk_data = {
            "id": "gen-1",
            "model": "anthropic/claude-3-opus",
            "choices": [{"index": 0, "delta": {"content": "Hi"}, "finish_reason": None}],
        }
        chunk = StreamChunk.from_dict(chunk_data)
        collector.add_chunk(chunk)

        assert collector.model == "anthropic/claude-3-opus"
