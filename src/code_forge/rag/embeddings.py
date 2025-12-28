"""Embedding providers for RAG system.

This module provides embedding generation using various backends:
- Local: sentence-transformers (default, no API cost)
- OpenAI: OpenAI embeddings API (higher quality, requires API key)

All providers use lazy loading to minimize startup impact.

Example:
    from code_forge.rag.embeddings import get_embedding_provider
    from code_forge.rag.config import RAGConfig

    config = RAGConfig()
    provider = get_embedding_provider(config)

    # Generate embedding
    embedding = await provider.embed("Hello, world!")

    # Batch embedding (more efficient)
    embeddings = await provider.embed_batch(["Hello", "World"])
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config import RAGConfig

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    All embedding providers must implement this interface to ensure
    consistent behavior across different backends.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name being used.

        Returns:
            The model identifier string.
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get the embedding dimension.

        Returns:
            The size of embedding vectors.
        """
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: The text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently.

        This is more efficient than calling embed() multiple times
        as it can batch the operations.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        ...


class SentenceTransformerProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers.

    This provider uses the sentence-transformers library to generate
    embeddings locally without any API calls. The model is loaded
    lazily on first use.

    Default model: all-MiniLM-L6-v2
    - Fast and efficient
    - 384 dimensions
    - Good for semantic similarity

    Attributes:
        _model_name: Name of the sentence-transformers model.
        _model: Lazy-loaded model instance.
        _dimension: Cached embedding dimension.
    """

    # Common model dimensions (to avoid loading model just for dimension)
    _KNOWN_DIMENSIONS: dict[str, int] = {
        "all-MiniLM-L6-v2": 384,
        "all-MiniLM-L12-v2": 384,
        "all-mpnet-base-v2": 768,
        "paraphrase-MiniLM-L6-v2": 384,
        "paraphrase-mpnet-base-v2": 768,
        "multi-qa-MiniLM-L6-cos-v1": 384,
        "multi-qa-mpnet-base-dot-v1": 768,
    }

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize the provider.

        Args:
            model_name: Name of the sentence-transformers model to use.
        """
        self._model_name = model_name
        self._model: Any = None
        self._dimension: int | None = self._KNOWN_DIMENSIONS.get(model_name)
        self._lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Get the embedding dimension.

        For known models, returns cached dimension without loading the model.
        For unknown models, loads the model to get the dimension.
        """
        if self._dimension is not None:
            return self._dimension
        # Need to load model to get dimension
        model = self._get_model_sync()
        self._dimension = model.get_sentence_embedding_dimension()
        return self._dimension

    def _get_model_sync(self) -> Any:
        """Get or load the model (synchronous).

        Returns:
            The sentence-transformers model instance.

        Raises:
            ImportError: If sentence-transformers is not installed.
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers is required for local embeddings. "
                    "Install with: pip install 'code-forge[rag]'"
                ) from e

            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            dim = self._model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Dimension: {dim}")
        return self._model

    async def _get_model(self) -> Any:
        """Get or load the model (async, thread-safe).

        Returns:
            The sentence-transformers model instance.
        """
        if self._model is not None:
            return self._model

        async with self._lock:
            if self._model is not None:
                return self._model

            # Load in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._get_model_sync)
            return self._model

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: The text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        model = await self._get_model()
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, lambda: model.encode(text, convert_to_numpy=True)
        )
        result: list[float] = embedding.tolist()
        return result

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        model = await self._get_model()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.encode(texts, convert_to_numpy=True, show_progress_bar=False),
        )
        return [e.tolist() for e in embeddings]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI API.

    This provider uses the OpenAI embeddings API for high-quality
    embeddings. Requires an OpenAI API key.

    Default model: text-embedding-3-small
    - 1536 dimensions
    - Good balance of quality and cost

    Attributes:
        _model_name: Name of the OpenAI embedding model.
        _client: Lazy-loaded OpenAI client.
        _api_key: OpenAI API key.
    """

    _KNOWN_DIMENSIONS: dict[str, int] = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: str | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            model_name: Name of the OpenAI embedding model.
            api_key: OpenAI API key (or uses OPENAI_API_KEY env var).
        """
        self._model_name = model_name
        self._api_key = api_key
        self._client: Any = None
        self._dimension: int | None = self._KNOWN_DIMENSIONS.get(model_name)
        self._lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self._dimension is not None:
            return self._dimension
        # Default for unknown models
        return 1536

    def _get_client_sync(self) -> Any:
        """Get or create the OpenAI client (synchronous).

        Returns:
            The OpenAI client instance.

        Raises:
            ImportError: If openai is not installed.
            ValueError: If no API key is available.
        """
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError(
                    "openai is required for OpenAI embeddings. "
                    "Install with: pip install openai"
                ) from e

            import os

            api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                    "or pass api_key parameter."
                )

            self._client = OpenAI(api_key=api_key)
        return self._client

    async def _get_client(self) -> Any:
        """Get or create the OpenAI client (async, thread-safe)."""
        if self._client is not None:
            return self._client

        async with self._lock:
            if self._client is not None:
                return self._client

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._get_client_sync)
            return self._client

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: The text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        client = await self._get_client()
        loop = asyncio.get_event_loop()

        def _embed() -> list[float]:
            response = client.embeddings.create(
                model=self._model_name,
                input=text,
            )
            embedding: list[float] = response.data[0].embedding
            return embedding

        return await loop.run_in_executor(None, _embed)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        client = await self._get_client()
        loop = asyncio.get_event_loop()

        def _embed_batch() -> list[list[float]]:
            response = client.embeddings.create(
                model=self._model_name,
                input=texts,
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [d.embedding for d in sorted_data]

        return await loop.run_in_executor(None, _embed_batch)


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing.

    Generates deterministic embeddings based on text hash.
    Useful for unit tests without loading real models.
    """

    def __init__(self, dimension: int = 384) -> None:
        """Initialize the mock provider.

        Args:
            dimension: Dimension of mock embeddings.
        """
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "mock-embedding"

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic embedding based on text hash.

        Args:
            text: The text to embed.

        Returns:
            Deterministic embedding vector.
        """
        import hashlib

        # Create deterministic embedding from text hash
        h = hashlib.sha256(text.encode()).hexdigest()
        # Use hash characters to generate floats
        embedding = []
        for i in range(self._dimension):
            char = h[i % len(h)]
            value = int(char, 16) / 15.0  # Normalize to 0-1
            embedding.append(value * 2 - 1)  # Scale to -1 to 1
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        return [await self.embed(text) for text in texts]


def get_embedding_provider(config: RAGConfig) -> EmbeddingProvider:
    """Get the appropriate embedding provider based on configuration.

    Args:
        config: RAG configuration.

    Returns:
        Configured embedding provider.

    Raises:
        ValueError: If an unknown provider type is specified.
    """
    from .config import EmbeddingProviderType

    if config.embedding_provider == EmbeddingProviderType.LOCAL:
        return SentenceTransformerProvider(model_name=config.embedding_model)
    elif config.embedding_provider == EmbeddingProviderType.OPENAI:
        return OpenAIEmbeddingProvider(model_name=config.openai_embedding_model)
    else:
        raise ValueError(f"Unknown embedding provider: {config.embedding_provider}")
