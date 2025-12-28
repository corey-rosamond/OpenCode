"""Tests for RAG embedding providers."""

import asyncio

import pytest

from code_forge.rag.config import EmbeddingProviderType, RAGConfig
from code_forge.rag.embeddings import (
    EmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    SentenceTransformerProvider,
    get_embedding_provider,
)


class TestMockEmbeddingProvider:
    """Tests for MockEmbeddingProvider."""

    def test_model_name(self) -> None:
        """Test model name property."""
        provider = MockEmbeddingProvider()
        assert provider.model_name == "mock-embedding"

    def test_dimension_default(self) -> None:
        """Test default dimension."""
        provider = MockEmbeddingProvider()
        assert provider.dimension == 384

    def test_dimension_custom(self) -> None:
        """Test custom dimension."""
        provider = MockEmbeddingProvider(dimension=768)
        assert provider.dimension == 768

    def test_embed_single(self) -> None:
        """Test embedding a single text."""
        provider = MockEmbeddingProvider(dimension=384)
        embedding = asyncio.get_event_loop().run_until_complete(
            provider.embed("Hello, world!")
        )
        assert len(embedding) == 384
        assert all(isinstance(v, float) for v in embedding)
        assert all(-1 <= v <= 1 for v in embedding)

    def test_embed_deterministic(self) -> None:
        """Test that embeddings are deterministic."""
        provider = MockEmbeddingProvider()
        loop = asyncio.get_event_loop()
        embedding1 = loop.run_until_complete(provider.embed("Hello, world!"))
        embedding2 = loop.run_until_complete(provider.embed("Hello, world!"))
        assert embedding1 == embedding2

    def test_embed_different_texts(self) -> None:
        """Test that different texts produce different embeddings."""
        provider = MockEmbeddingProvider()
        loop = asyncio.get_event_loop()
        embedding1 = loop.run_until_complete(provider.embed("Hello"))
        embedding2 = loop.run_until_complete(provider.embed("World"))
        assert embedding1 != embedding2

    def test_embed_batch(self) -> None:
        """Test batch embedding."""
        provider = MockEmbeddingProvider(dimension=384)
        texts = ["Hello", "World", "Test"]
        embeddings = asyncio.get_event_loop().run_until_complete(
            provider.embed_batch(texts)
        )
        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)

    def test_embed_batch_empty(self) -> None:
        """Test batch embedding with empty list."""
        provider = MockEmbeddingProvider()
        embeddings = asyncio.get_event_loop().run_until_complete(
            provider.embed_batch([])
        )
        assert embeddings == []


class TestSentenceTransformerProvider:
    """Tests for SentenceTransformerProvider."""

    def test_model_name(self) -> None:
        """Test model name property."""
        provider = SentenceTransformerProvider(model_name="test-model")
        assert provider.model_name == "test-model"

    def test_dimension_known_model(self) -> None:
        """Test dimension for known models."""
        provider = SentenceTransformerProvider(model_name="all-MiniLM-L6-v2")
        # Should return cached dimension without loading model
        assert provider.dimension == 384

    def test_dimension_known_models(self) -> None:
        """Test dimension caching for known models."""
        models_and_dims = [
            ("all-MiniLM-L6-v2", 384),
            ("all-MiniLM-L12-v2", 384),
            ("all-mpnet-base-v2", 768),
            ("paraphrase-MiniLM-L6-v2", 384),
        ]
        for model_name, expected_dim in models_and_dims:
            provider = SentenceTransformerProvider(model_name=model_name)
            assert provider.dimension == expected_dim


class TestOpenAIEmbeddingProvider:
    """Tests for OpenAIEmbeddingProvider."""

    def test_model_name(self) -> None:
        """Test model name property."""
        provider = OpenAIEmbeddingProvider(model_name="text-embedding-3-small")
        assert provider.model_name == "text-embedding-3-small"

    def test_dimension_known_model(self) -> None:
        """Test dimension for known models."""
        provider = OpenAIEmbeddingProvider(model_name="text-embedding-3-small")
        assert provider.dimension == 1536

    def test_dimension_unknown_model(self) -> None:
        """Test dimension for unknown models defaults to 1536."""
        provider = OpenAIEmbeddingProvider(model_name="unknown-model")
        assert provider.dimension == 1536


class TestGetEmbeddingProvider:
    """Tests for get_embedding_provider factory function."""

    def test_get_local_provider(self) -> None:
        """Test getting local embedding provider."""
        config = RAGConfig(
            embedding_provider=EmbeddingProviderType.LOCAL,
            embedding_model="all-MiniLM-L6-v2",
        )
        provider = get_embedding_provider(config)
        assert isinstance(provider, SentenceTransformerProvider)
        assert provider.model_name == "all-MiniLM-L6-v2"

    def test_get_openai_provider(self) -> None:
        """Test getting OpenAI embedding provider."""
        config = RAGConfig(
            embedding_provider=EmbeddingProviderType.OPENAI,
            openai_embedding_model="text-embedding-3-small",
        )
        provider = get_embedding_provider(config)
        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert provider.model_name == "text-embedding-3-small"


class TestEmbeddingProviderProtocol:
    """Tests to verify providers implement the protocol correctly."""

    def test_mock_provider_is_embedding_provider(self) -> None:
        """Test MockEmbeddingProvider implements protocol."""
        provider = MockEmbeddingProvider()
        # Verify it has all required attributes/methods
        assert hasattr(provider, "model_name")
        assert hasattr(provider, "dimension")
        assert hasattr(provider, "embed")
        assert hasattr(provider, "embed_batch")

    def test_sentence_transformer_is_embedding_provider(self) -> None:
        """Test SentenceTransformerProvider implements protocol."""
        provider = SentenceTransformerProvider()
        assert hasattr(provider, "model_name")
        assert hasattr(provider, "dimension")
        assert hasattr(provider, "embed")
        assert hasattr(provider, "embed_batch")

    def test_openai_is_embedding_provider(self) -> None:
        """Test OpenAIEmbeddingProvider implements protocol."""
        provider = OpenAIEmbeddingProvider()
        assert hasattr(provider, "model_name")
        assert hasattr(provider, "dimension")
        assert hasattr(provider, "embed")
        assert hasattr(provider, "embed_batch")
