"""Tests for Gemini LLM and embedding providers (mocked SDK)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.core.llm import LLMUsage


class TestGeminiLLMProvider:
    """Tests for GeminiLLMProvider with mocked SDK."""

    def test_missing_api_key_raises(self) -> None:
        """Test that missing API key raises ValueError."""
        from app.core.llm.providers.gemini import GeminiLLMProvider

        with pytest.raises(ValueError, match="API key is required"):
            GeminiLLMProvider(api_key="")

    def test_provider_properties(self) -> None:
        """Test provider metadata."""
        from app.core.llm.providers.gemini import GeminiLLMProvider

        with patch("google.genai.Client"):
            provider = GeminiLLMProvider(api_key="test-key")
            assert provider.provider_name == "gemini"
            assert provider.model == "gemini-3.8-flash"

    @pytest.mark.asyncio
    async def test_generate_text(self) -> None:
        """Test normal text generation with mocked SDK."""
        from app.core.llm.providers.gemini import GeminiLLMProvider

        mock_response = MagicMock()
        mock_response.text = "Hello, world!"
        mock_response.parsed = None
        mock_response.usage_metadata = None

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            provider = GeminiLLMProvider(api_key="test-key")
            response = await provider.generate(
                [{"role": "user", "content": "Say hello"}]
            )

            assert response.content == "Hello, world!"
            assert response.provider == "gemini"
            assert response.structured_output is None

    @pytest.mark.asyncio
    async def test_generate_structured(self) -> None:
        """Test structured output generation with mocked SDK."""
        from app.core.llm.providers.gemini import GeminiLLMProvider
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            name: str
            score: float

        mock_response = MagicMock()
        mock_response.text = '{"name": "test", "score": 0.9}'
        mock_response.parsed = TestSchema(name="test", score=0.9)
        mock_response.usage_metadata = None

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            provider = GeminiLLMProvider(api_key="test-key")
            result = await provider.generate_structured(
                [{"role": "user", "content": "Generate"}],
                TestSchema,
            )

            assert isinstance(result, TestSchema)
            assert result.name == "test"
            assert result.score == 0.9

    @pytest.mark.asyncio
    async def test_malformed_structured_output_raises(self) -> None:
        """Test that malformed structured output raises ValueError."""
        from app.core.llm.providers.gemini import GeminiLLMProvider
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            name: str
            score: float

        mock_response = MagicMock()
        mock_response.text = "not json"
        mock_response.parsed = None
        mock_response.usage_metadata = None

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            provider = GeminiLLMProvider(api_key="test-key")
            # generate() should return None structured_output
            response = await provider.generate(
                [{"role": "user", "content": "Generate"}],
                response_schema=TestSchema,
            )
            assert response.structured_output is None

    @pytest.mark.asyncio
    async def test_usage_metadata_mapping(self) -> None:
        """Test that usage metadata is correctly mapped."""
        from app.core.llm.providers.gemini import GeminiLLMProvider

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 20
        mock_usage.total_token_count = 30

        mock_response = MagicMock()
        mock_response.text = "Hello"
        mock_response.parsed = None
        mock_response.usage_metadata = mock_usage

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            provider = GeminiLLMProvider(api_key="test-key")
            response = await provider.generate(
                [{"role": "user", "content": "Hello"}]
            )

            assert response.usage.input_tokens == 10
            assert response.usage.output_tokens == 20
            assert response.usage.total_tokens == 30

    @pytest.mark.asyncio
    async def test_api_key_not_in_error(self) -> None:
        """Test that API key is not exposed in errors."""
        from app.core.llm.providers.gemini import GeminiLLMProvider

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception(
                "API key invalid"
            )
            mock_client_cls.return_value = mock_client

            provider = GeminiLLMProvider(api_key="secret-key-123")
            with pytest.raises(Exception) as exc_info:
                await provider.generate([{"role": "user", "content": "Hello"}])

            # The error message should not contain the API key.
            assert "secret-key-123" not in str(exc_info.value)


class TestGeminiEmbeddingProvider:
    """Tests for GeminiEmbeddingProvider with mocked SDK."""

    def test_missing_api_key_raises(self) -> None:
        """Test that missing API key raises ValueError."""
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        with pytest.raises(ValueError, match="API key is required"):
            GeminiEmbeddingProvider(api_key="")

    def test_provider_properties(self) -> None:
        """Test provider metadata."""
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        with patch("google.genai.Client"):
            provider = GeminiEmbeddingProvider(api_key="test-key")
            assert provider.provider_name == "gemini"
            assert provider.model == "gemini-embedding-2"
            assert provider.dimension == 384

    @pytest.mark.asyncio
    async def test_embed_text(self) -> None:
        """Test single text embedding."""
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        mock_emb = MagicMock()
        mock_emb.values = [0.1] * 384

        mock_response = MagicMock()
        mock_response.embeddings = [mock_emb]

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.embed_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            provider = GeminiEmbeddingProvider(api_key="test-key")
            vec = await provider.embed_text("Hello")

            assert len(vec) == 384
            assert vec[0] == 0.1

    @pytest.mark.asyncio
    async def test_embed_documents(self) -> None:
        """Test batch document embedding."""
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        mock_emb1 = MagicMock()
        mock_emb1.values = [0.1] * 384
        mock_emb2 = MagicMock()
        mock_emb2.values = [0.2] * 384

        mock_response = MagicMock()
        mock_response.embeddings = [mock_emb1, mock_emb2]

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.embed_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            provider = GeminiEmbeddingProvider(api_key="test-key")
            vecs = await provider.embed_documents(["Hello", "World"])

            assert len(vecs) == 2
            assert all(len(v) == 384 for v in vecs)

    @pytest.mark.asyncio
    async def test_wrong_dimension_raises(self) -> None:
        """Test that wrong embedding dimension raises error."""
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        mock_emb = MagicMock()
        mock_emb.values = [0.1] * 100  # Wrong dimension

        mock_response = MagicMock()
        mock_response.embeddings = [mock_emb]

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.embed_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            provider = GeminiEmbeddingProvider(api_key="test-key")
            with pytest.raises(ValueError, match="dimension mismatch"):
                await provider.embed_text("Hello")

    @pytest.mark.asyncio
    async def test_empty_documents(self) -> None:
        """Test empty document list."""
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        with patch("google.genai.Client"):
            provider = GeminiEmbeddingProvider(api_key="test-key")
            vecs = await provider.embed_documents([])
            assert vecs == []

    @pytest.mark.asyncio
    async def test_api_key_not_in_error(self) -> None:
        """Test that API key is not exposed in errors."""
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.embed_content.side_effect = Exception(
                "API key invalid"
            )
            mock_client_cls.return_value = mock_client

            provider = GeminiEmbeddingProvider(api_key="secret-key-456")
            with pytest.raises(Exception) as exc_info:
                await provider.embed_text("Hello")

            assert "secret-key-456" not in str(exc_info.value)


class TestProviderFactory:
    """Tests for provider factory functions."""

    def test_fake_llm_provider_selectable(self) -> None:
        """Test that fake LLM provider is selectable."""
        import os
        from unittest.mock import patch, MagicMock
        os.environ["LLM_PROVIDER"] = "fake"

        mock_settings = MagicMock()
        mock_settings.llm_provider = "fake"

        with patch("app.core.providers.get_settings", return_value=mock_settings):
            from app.core.providers import create_llm_provider
            from app.core.llm import FakeLLMProvider

            provider = create_llm_provider()
            assert isinstance(provider, FakeLLMProvider)

    def test_fake_embedding_provider_selectable(self) -> None:
        """Test that fake embedding provider is selectable."""
        import os
        from unittest.mock import patch, MagicMock
        os.environ["EMBEDDING_PROVIDER"] = "fake"

        mock_settings = MagicMock()
        mock_settings.embedding_provider = "fake"

        with patch("app.core.providers.get_settings", return_value=mock_settings):
            from app.core.providers import create_embedding_provider
            from app.core.embedding import FakeEmbeddingProvider

            provider = create_embedding_provider()
            assert isinstance(provider, FakeEmbeddingProvider)

    def test_gemini_llm_provider_selectable(self) -> None:
        """Test that gemini LLM provider is selectable with API key."""
        import os
        from unittest.mock import patch, MagicMock
        os.environ["LLM_PROVIDER"] = "gemini"

        mock_settings = MagicMock()
        mock_settings.llm_provider = "gemini"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_model = "gemini-3.8-flash"

        with patch("app.core.providers.get_settings", return_value=mock_settings):
            with patch("google.genai.Client"):
                from app.core.providers import create_llm_provider
                from app.core.llm.providers.gemini import GeminiLLMProvider

                provider = create_llm_provider()
                assert isinstance(provider, GeminiLLMProvider)

    def test_gemini_embedding_provider_selectable(self) -> None:
        """Test that gemini embedding provider is selectable with API key."""
        import os
        from unittest.mock import patch, MagicMock
        os.environ["EMBEDDING_PROVIDER"] = "gemini"

        mock_settings = MagicMock()
        mock_settings.embedding_provider = "gemini"
        mock_settings.embedding_api_key = "test-key"
        mock_settings.embedding_model = "gemini-embedding-2"
        mock_settings.embedding_dimension = 384

        with patch("app.core.providers.get_settings", return_value=mock_settings):
            with patch("google.genai.Client"):
                from app.core.providers import create_embedding_provider
                from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

                provider = create_embedding_provider()
                assert isinstance(provider, GeminiEmbeddingProvider)

    def test_gemini_llm_missing_key_raises(self) -> None:
        """Test that gemini LLM provider raises without API key."""
        import os
        from unittest.mock import patch, MagicMock
        os.environ["LLM_PROVIDER"] = "gemini"

        # Mock settings to return no API key
        mock_settings = MagicMock()
        mock_settings.llm_provider = "gemini"
        mock_settings.llm_api_key = None
        mock_settings.llm_model = "gemini-3.8-flash"

        with patch("app.core.providers.get_settings", return_value=mock_settings):
            from app.core.providers import create_llm_provider

            with pytest.raises(ValueError, match="LLM_API_KEY is required"):
                create_llm_provider()

    def test_gemini_embedding_missing_key_raises(self) -> None:
        """Test that gemini embedding provider raises without API key."""
        import os
        from unittest.mock import patch, MagicMock
        os.environ["EMBEDDING_PROVIDER"] = "gemini"

        # Mock settings to return no API key
        mock_settings = MagicMock()
        mock_settings.embedding_provider = "gemini"
        mock_settings.embedding_api_key = None
        mock_settings.embedding_model = "gemini-embedding-2"
        mock_settings.embedding_dimension = 384

        with patch("app.core.providers.get_settings", return_value=mock_settings):
            from app.core.providers import create_embedding_provider

            with pytest.raises(ValueError, match="EMBEDDING_API_KEY is required"):
                create_embedding_provider()
