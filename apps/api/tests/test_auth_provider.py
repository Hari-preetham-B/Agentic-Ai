"""Tests for authentication providers."""

from unittest.mock import MagicMock, patch

import jwt
import pytest
from app.core.auth.provider import FakeAuthProvider
from app.core.auth.supabase_provider import SupabaseAuthProvider


class TestFakeAuthProvider:
    """Tests for FakeAuthProvider."""

    @pytest.mark.asyncio
    async def test_valid_token(self) -> None:
        """Test that a valid fake token is accepted."""
        provider = FakeAuthProvider()
        result = await provider.validate_token("fake:user123:user@example.com")
        assert result.user_id == "user123"
        assert result.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_invalid_token(self) -> None:
        """Test that an invalid token raises ValueError."""
        provider = FakeAuthProvider()
        with pytest.raises(ValueError, match="Invalid authentication token"):
            await provider.validate_token("invalid-token")

    @pytest.mark.asyncio
    async def test_empty_token(self) -> None:
        """Test that an empty token raises ValueError."""
        provider = FakeAuthProvider()
        with pytest.raises(ValueError, match="Invalid authentication token"):
            await provider.validate_token("")

    @pytest.mark.asyncio
    async def test_missing_user_id(self) -> None:
        """Test that a token without user_id raises ValueError."""
        provider = FakeAuthProvider()
        with pytest.raises(ValueError, match="Invalid user ID in token"):
            await provider.validate_token("fake::email@test.com")


class TestSupabaseAuthProvider:
    """Tests for SupabaseAuthProvider with mocked JWKS."""

    @pytest.fixture
    def provider(self) -> SupabaseAuthProvider:
        return SupabaseAuthProvider(
            supabase_url="https://test-project.supabase.co",
        )

    @pytest.mark.asyncio
    async def test_valid_token(self, provider: SupabaseAuthProvider) -> None:
        """Test that a valid JWT is accepted."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake-public-key"

        mock_payload = MagicMock()
        mock_payload.get.side_effect = lambda key, default=None: {
            "sub": "user-123",
            "email": "user@example.com",
        }.get(key, default)

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.return_value = mock_payload

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.return_value = (
                    mock_signing_key
                )
                mock_jwks.return_value = mock_jwks_instance

                result = await provider.validate_token("valid-token")

                assert result.user_id == "user-123"
                assert result.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_expired_token(self, provider: SupabaseAuthProvider) -> None:
        """Test that an expired token is rejected."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake-public-key"

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.return_value = (
                    mock_signing_key
                )
                mock_jwks.return_value = mock_jwks_instance

                with pytest.raises(ValueError, match="Token has expired"):
                    await provider.validate_token("expired-token")

    @pytest.mark.asyncio
    async def test_invalid_signature(self, provider: SupabaseAuthProvider) -> None:
        """Test that a token with invalid signature is rejected."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake-public-key"

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidSignatureError("Bad signature")

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.return_value = (
                    mock_signing_key
                )
                mock_jwks.return_value = mock_jwks_instance

                with pytest.raises(ValueError, match="Invalid token"):
                    await provider.validate_token("bad-signature-token")

    @pytest.mark.asyncio
    async def test_missing_kid(self, provider: SupabaseAuthProvider) -> None:
        """Test that a token without a kid header is rejected."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake-public-key"

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidKeyError("No signing key found")

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.side_effect = (
                    jwt.InvalidKeyError("No signing key found")
                )
                mock_jwks.return_value = mock_jwks_instance

                with pytest.raises(ValueError):
                    await provider.validate_token("token-without-kid")

    @pytest.mark.asyncio
    async def test_unknown_kid_triggers_refresh(
        self, provider: SupabaseAuthProvider
    ) -> None:
        """Test that an unknown kid triggers a JWKS refresh and retry."""
        mock_signing_key_first = MagicMock()
        mock_signing_key_first.key = "old-key"
        mock_signing_key_second = MagicMock()
        mock_signing_key_second.key = "new-public-key"

        mock_payload = MagicMock()
        mock_payload.get.side_effect = lambda key, default=None: {
            "sub": "user-456",
            "email": "user@example.com",
        }.get(key, default)

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.return_value = mock_payload

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.side_effect = [
                    Exception("Key not found"),
                    mock_signing_key_second,
                ]
                mock_jwks.return_value = mock_jwks_instance

                result = await provider.validate_token("token-with-new-kid")

                assert result.user_id == "user-456"
                assert result.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_unsupported_algorithm(self, provider: SupabaseAuthProvider) -> None:
        """Test that an unsupported algorithm is rejected."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake-public-key"

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidAlgorithmError(
                "Unsupported algorithm"
            )

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.return_value = (
                    mock_signing_key
                )
                mock_jwks.return_value = mock_jwks_instance

                with pytest.raises(ValueError, match="Invalid token"):
                    await provider.validate_token("token-with-bad-alg")

    @pytest.mark.asyncio
    async def test_invalid_issuer(self, provider: SupabaseAuthProvider) -> None:
        """Test that a token with wrong issuer is rejected."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake-public-key"

        mock_payload = MagicMock()
        mock_payload.get.side_effect = lambda key, default=None: {
            "sub": "user-123",
            "email": "user@example.com",
        }.get(key, default)

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidIssuerError("Invalid issuer")

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.return_value = (
                    mock_signing_key
                )
                mock_jwks.return_value = mock_jwks_instance

                with pytest.raises(ValueError, match="Invalid token"):
                    await provider.validate_token("token-with-wrong-issuer")

    @pytest.mark.asyncio
    async def test_malformed_token(self, provider: SupabaseAuthProvider) -> None:
        """Test that a malformed token is rejected."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake-public-key"

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.DecodeError("Not enough segments")

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.return_value = (
                    mock_signing_key
                )
                mock_jwks.return_value = mock_jwks_instance

                with pytest.raises(ValueError, match="Invalid token"):
                    await provider.validate_token("not-a-jwt")

    @pytest.mark.asyncio
    async def test_jwks_endpoint_failure_fails_closed(
        self, provider: SupabaseAuthProvider
    ) -> None:
        """Test that JWKS endpoint failure results in FAILED status."""
        with patch(
            "app.core.auth.supabase_provider.PyJWKClient"
        ) as mock_jwks:
            mock_jwks.side_effect = Exception("Network error")

            with pytest.raises(ValueError, match="Unable to reach JWKS"):
                await provider.validate_token("any-token")

    @pytest.mark.asyncio
    async def test_jwks_cache_prevents_repeated_requests(
        self, provider: SupabaseAuthProvider
    ) -> None:
        """Test that the JWKS cache prevents repeated requests."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "cached-key"

        mock_payload = MagicMock()
        mock_payload.get.side_effect = lambda key, default=None: {
            "sub": "cached-user",
            "email": "cached@example.com",
        }.get(key, default)

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.return_value = mock_payload

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                mock_jwks_instance.get_signing_key_from_jwt.return_value = (
                    mock_signing_key
                )
                mock_jwks.return_value = mock_jwks_instance

                # First call
                await provider.validate_token("token-1")
                # Second call - should use cached JWKS
                await provider.validate_token("token-2")

                # PyJWKClient should only be instantiated once
                assert mock_jwks.call_count == 1

    @pytest.mark.asyncio
    async def test_unknown_kid_succeeds_after_refresh(
        self, provider: SupabaseAuthProvider
    ) -> None:
        """Test that an unknown kid succeeds after JWKS refresh."""
        mock_signing_key_first = MagicMock()
        mock_signing_key_first.key = "old-key"
        mock_signing_key_second = MagicMock()
        mock_signing_key_second.key = "new-public-key"

        mock_payload = MagicMock()
        mock_payload.get.side_effect = lambda key, default=None: {
            "sub": "user-456",
            "email": "user@example.com",
        }.get(key, default)

        with patch("app.core.auth.supabase_provider.jwt.decode") as mock_decode:
            mock_decode.return_value = mock_payload

            with patch(
                "app.core.auth.supabase_provider.PyJWKClient"
            ) as mock_jwks:
                mock_jwks_instance = MagicMock()
                # First call raises (unknown key), second succeeds
                mock_jwks_instance.get_signing_key_from_jwt.side_effect = [
                    Exception("Key not found"),
                    mock_signing_key_second,
                ]
                mock_jwks.return_value = mock_jwks_instance

                result = await provider.validate_token("token-with-new-kid")

                assert result.user_id == "user-456"
                assert result.email == "user@example.com"


class TestAuthProviderFactory:
    """Tests for provider factory selection."""

    def test_fake_provider_selected_by_default(self) -> None:
        """Test that fake provider is used when no Supabase URL is set."""
        from unittest.mock import patch, MagicMock
        from app.core.providers import create_llm_provider
        from app.core.llm.fake import FakeLLMProvider

        mock_settings = MagicMock()
        mock_settings.llm_provider = "fake"

        with patch("app.core.providers.get_settings", return_value=mock_settings):
            provider = create_llm_provider()
            assert isinstance(provider, FakeLLMProvider)

    def test_gemini_provider_selectable(self) -> None:
        """Test that gemini LLM provider is selectable with API key."""
        import os
        from app.core.providers import create_llm_provider
        from app.core.llm.providers.gemini import GeminiLLMProvider

        os.environ["LLM_PROVIDER"] = "gemini"
        os.environ["LLM_API_KEY"] = "test-key"
        os.environ["LLM_MODEL"] = "gemini-3.8-flash"

        try:
            from app.core.config import get_settings

            get_settings.cache_clear()
            with patch("google.genai.Client"):
                provider = create_llm_provider()
                assert isinstance(provider, GeminiLLMProvider)
        finally:
            os.environ.pop("LLM_PROVIDER", None)
            os.environ.pop("LLM_API_KEY", None)
            os.environ.pop("LLM_MODEL", None)
            from app.core.config import get_settings

            get_settings.cache_clear()

    def test_gemini_embedding_provider_selectable(self) -> None:
        """Test that gemini embedding provider is selectable."""
        import os
        from app.core.providers import create_embedding_provider
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        os.environ["EMBEDDING_PROVIDER"] = "gemini"
        os.environ["EMBEDDING_API_KEY"] = "test-key"
        os.environ["EMBEDDING_MODEL"] = "gemini-embedding-2"
        os.environ["EMBEDDING_DIMENSION"] = "384"

        try:
            from app.core.config import get_settings

            get_settings.cache_clear()
            with patch("google.genai.Client"):
                provider = create_embedding_provider()
                assert isinstance(provider, GeminiEmbeddingProvider)
        finally:
            os.environ.pop("EMBEDDING_PROVIDER", None)
            os.environ.pop("EMBEDDING_API_KEY", None)
            os.environ.pop("EMBEDDING_MODEL", None)
            os.environ.pop("EMBEDDING_DIMENSION", None)
            from app.core.config import get_settings

            get_settings.cache_clear()

    def test_gemini_llm_missing_key_raises(self) -> None:
        """Test that gemini LLM provider raises without API key."""
        import os
        from app.core.providers import create_llm_provider

        os.environ["LLM_PROVIDER"] = "gemini"
        os.environ["LLM_API_KEY"] = ""  # Override .env file value

        try:
            from app.core.providers import create_llm_provider

            with pytest.raises(ValueError, match="LLM_API_KEY is required"):
                create_llm_provider()
        finally:
            os.environ.pop("LLM_PROVIDER", None)
            os.environ.pop("LLM_API_KEY", None)

    def test_gemini_embedding_missing_key_raises(self) -> None:
        """Test that gemini embedding provider raises without API key."""
        import os
        from app.core.providers import create_embedding_provider

        os.environ["EMBEDDING_PROVIDER"] = "gemini"
        os.environ["EMBEDDING_API_KEY"] = ""  # Override .env file value

        try:
            from app.core.providers import create_embedding_provider

            with pytest.raises(ValueError, match="EMBEDDING_API_KEY is required"):
                create_embedding_provider()
        finally:
            os.environ.pop("EMBEDDING_PROVIDER", None)
            os.environ.pop("EMBEDDING_API_KEY", None)