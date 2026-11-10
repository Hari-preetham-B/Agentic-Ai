"""Tests for authentication providers."""

import time
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
    """Tests for SupabaseAuthProvider using real signed tokens."""

    URL = "https://test-project.supabase.co"
    SECRET = "x" * 48

    @pytest.fixture(scope="class")
    def ec_key(self):
        from cryptography.hazmat.primitives.asymmetric import ec

        return ec.generate_private_key(ec.SECP256R1())

    def _claims(self, **over):
        now = int(time.time())
        claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "aud": "authenticated",
            "iss": f"{self.URL}/auth/v1",
            "iat": now,
            "exp": now + 600,
        }
        claims.update(over)
        return claims

    def _es256(self, ec_key, **over):
        return jwt.encode(self._claims(**over), ec_key, algorithm="ES256", headers={"kid": "k1"})

    def _provider(self, ec_key, secret=None):
        provider = SupabaseAuthProvider(supabase_url=self.URL, jwt_secret=secret)
        signing_key = MagicMock()
        signing_key.key = ec_key.public_key()
        signing_key.algorithm_name = "ES256"
        client = MagicMock()
        client.get_signing_key_from_jwt.return_value = signing_key
        provider._jwks_client = client
        provider._jwks_fetch_time = time.time()
        return provider, client

    @pytest.mark.asyncio
    async def test_valid_es256_token(self, ec_key) -> None:
        provider, _ = self._provider(ec_key)
        user = await provider.validate_token(self._es256(ec_key))
        assert user.user_id == "user-123"
        assert user.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_expired_token(self, ec_key) -> None:
        provider, _ = self._provider(ec_key)
        token = self._es256(ec_key, exp=int(time.time()) - 10)
        with pytest.raises(ValueError, match="expired"):
            await provider.validate_token(token)

    @pytest.mark.asyncio
    async def test_wrong_signature_rejected(self, ec_key) -> None:
        from cryptography.hazmat.primitives.asymmetric import ec

        provider, _ = self._provider(ec_key)
        other = ec.generate_private_key(ec.SECP256R1())
        with pytest.raises(ValueError, match="Invalid token"):
            await provider.validate_token(self._es256(other))

    @pytest.mark.asyncio
    async def test_wrong_issuer_rejected(self, ec_key) -> None:
        provider, _ = self._provider(ec_key)
        with pytest.raises(ValueError, match="Invalid token"):
            await provider.validate_token(self._es256(ec_key, iss="https://evil.example/auth/v1"))

    @pytest.mark.asyncio
    async def test_wrong_audience_rejected(self, ec_key) -> None:
        provider, _ = self._provider(ec_key)
        with pytest.raises(ValueError, match="Invalid token"):
            await provider.validate_token(self._es256(ec_key, aud="anon"))

    @pytest.mark.asyncio
    async def test_missing_subject_rejected(self, ec_key) -> None:
        provider, _ = self._provider(ec_key)
        claims = self._claims()
        del claims["sub"]
        token = jwt.encode(claims, ec_key, algorithm="ES256", headers={"kid": "k1"})
        with pytest.raises(ValueError, match="Invalid token"):
            await provider.validate_token(token)

    @pytest.mark.asyncio
    async def test_malformed_token(self, ec_key) -> None:
        provider, _ = self._provider(ec_key)
        with pytest.raises(ValueError, match="Invalid token"):
            await provider.validate_token("not-a-jwt")

    @pytest.mark.asyncio
    async def test_empty_token(self, ec_key) -> None:
        provider, _ = self._provider(ec_key)
        with pytest.raises(ValueError, match="Missing"):
            await provider.validate_token("")

    @pytest.mark.asyncio
    async def test_unsupported_jwks_algorithm(self, ec_key) -> None:
        provider, client = self._provider(ec_key)
        client.get_signing_key_from_jwt.return_value.algorithm_name = "none"
        with pytest.raises(ValueError, match="Unsupported"):
            await provider.validate_token(self._es256(ec_key))

    @pytest.mark.asyncio
    async def test_jwks_unreachable_fails_closed(self, ec_key) -> None:
        provider, client = self._provider(ec_key)
        client.get_signing_key_from_jwt.side_effect = RuntimeError("network down")
        with patch.object(provider, "_get_jwks_client", return_value=client):
            with pytest.raises(ValueError, match="signing key"):
                await provider.validate_token(self._es256(ec_key))

    @pytest.mark.asyncio
    async def test_jwks_cache_reused(self, ec_key) -> None:
        provider, _ = self._provider(ec_key)
        first = provider._get_jwks_client()
        assert provider._get_jwks_client() is first

    # -- legacy HS256 projects ------------------------------------------

    @pytest.mark.asyncio
    async def test_hs256_accepted_with_secret(self) -> None:
        provider = SupabaseAuthProvider(supabase_url=self.URL, jwt_secret=self.SECRET)
        token = jwt.encode(self._claims(), self.SECRET, algorithm="HS256")
        user = await provider.validate_token(token)
        assert user.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_hs256_rejected_without_secret(self) -> None:
        provider = SupabaseAuthProvider(supabase_url=self.URL)
        token = jwt.encode(self._claims(), self.SECRET, algorithm="HS256")
        with pytest.raises(ValueError, match="SUPABASE_JWT_SECRET"):
            await provider.validate_token(token)

    @pytest.mark.asyncio
    async def test_hs256_wrong_secret_rejected(self) -> None:
        provider = SupabaseAuthProvider(supabase_url=self.URL, jwt_secret=self.SECRET)
        token = jwt.encode(self._claims(), "y" * 48, algorithm="HS256")
        with pytest.raises(ValueError, match="Invalid token"):
            await provider.validate_token(token)


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