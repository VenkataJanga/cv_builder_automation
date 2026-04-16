"""
Test suite to validate API key configuration and connectivity.
Tests OpenAI API key from .env file to ensure it's working correctly.
"""

import os
import pytest
from pathlib import Path
from openai import OpenAI, AzureOpenAI


class TestAPIKeyValidation:
    """Tests to verify API keys are properly configured and working."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load environment variables before each test."""
        from src.core.env_loader import load_environment_variables
        load_environment_variables()

    def test_openai_api_key_exists(self):
        """Test that OPENAI_API_KEY is present in environment."""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY not found in .env file"
        assert api_key.strip() != "", "OPENAI_API_KEY is empty"
        assert api_key.startswith("sk-"), "OPENAI_API_KEY should start with 'sk-'"

    def test_openai_model_configuration_exists(self):
        """Test that OpenAI model configurations are present."""
        model = os.getenv("OPENAI_MODEL")
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL")
        
        assert model is not None, "OPENAI_MODEL not configured"
        assert embedding_model is not None, "OPENAI_EMBEDDING_MODEL not configured"
        assert model.strip() != "", "OPENAI_MODEL is empty"
        assert embedding_model.strip() != "", "OPENAI_EMBEDDING_MODEL is empty"

    def test_openai_client_initialization(self):
        """Test that OpenAI client can be initialized with the API key."""
        api_key = os.getenv("OPENAI_API_KEY")
        try:
            client = OpenAI(api_key=api_key)
            # Verify client has required attributes
            assert hasattr(client, 'chat'), "OpenAI client missing 'chat' attribute"
            assert hasattr(client, 'embeddings'), "OpenAI client missing 'embeddings' attribute"
        except Exception as e:
            pytest.fail(f"Failed to initialize OpenAI client: {str(e)}")

    def test_openai_chat_api_connectivity(self):
        """Test basic connectivity to OpenAI Chat API."""
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        client = OpenAI(api_key=api_key)
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'API Key is valid' in one sentence."}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            assert response is not None, "Chat API returned None"
            assert response.choices, "No choices returned from Chat API"
            assert response.choices[0].message.content, "Empty message content from Chat API"
            assert "valid" in response.choices[0].message.content.lower() or \
                   "API" in response.choices[0].message.content, \
                   "Unexpected response from Chat API"
            
        except Exception as e:
            pytest.fail(f"OpenAI Chat API test failed: {str(e)}")

    def test_openai_embedding_api_connectivity(self):
        """Test basic connectivity to OpenAI Embedding API."""
        api_key = os.getenv("OPENAI_API_KEY")
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        
        client = OpenAI(api_key=api_key)
        
        try:
            response = client.embeddings.create(
                model=embedding_model,
                input="API key validation test"
            )
            
            assert response is not None, "Embedding API returned None"
            assert response.data, "No embeddings returned from Embedding API"
            assert response.data[0].embedding, "Empty embedding vector"
            assert isinstance(response.data[0].embedding, list), "Embedding is not a list"
            assert len(response.data[0].embedding) > 0, "Embedding vector is empty"
            
        except Exception as e:
            pytest.fail(f"OpenAI Embedding API test failed: {str(e)}")

    def test_azure_openai_optional_config(self):
        """Test that Azure OpenAI configuration is optional (doesn't error if missing)."""
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        # Azure config is optional - just verify no error if partially configured
        if azure_endpoint and azure_api_key:
            try:
                client = AzureOpenAI(
                    api_key=azure_api_key,
                    api_version="2024-02-15-preview",
                    azure_endpoint=azure_endpoint
                )
                assert client is not None, "Failed to initialize Azure OpenAI client"
            except Exception as e:
                pytest.fail(f"Failed to initialize Azure OpenAI client: {str(e)}")
        else:
            # Azure is optional, just verify primary OpenAI is configured
            assert os.getenv("OPENAI_API_KEY"), "No API key configured (neither OpenAI nor Azure)"

    def test_api_key_format_validation(self):
        """Test that API keys have valid format."""
        api_key = os.getenv("OPENAI_API_KEY")
        
        # OpenAI format: sk-proj-... or sk-...
        valid_openai_format = (
            api_key.startswith("sk-proj-") or 
            (api_key.startswith("sk-") and not api_key.startswith("sk-proj-"))
        )
        assert valid_openai_format, f"Invalid OpenAI API key format: {api_key[:20]}..."

    def test_environment_variables_are_loaded(self):
        """Test that all required environment variables are loaded."""
        required_vars = [
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "OPENAI_EMBEDDING_MODEL",
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            assert value is not None, f"Required environment variable '{var}' not found"
            assert value.strip() != "", f"Environment variable '{var}' is empty"


class TestAPIKeyIntegration:
    """Integration tests for API key usage in the application."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load environment variables before each test."""
        from src.core.env_loader import load_environment_variables
        load_environment_variables()

    def test_openai_provider_can_be_imported(self):
        """Test that OpenAI provider can be imported without errors."""
        try:
            from src.ai.providers.chat.openai_provider import OpenAIProvider
            assert OpenAIProvider is not None, "OpenAIProvider import failed"
        except Exception as e:
            pytest.fail(f"Failed to import OpenAIProvider: {str(e)}")

    def test_embeddings_provider_can_be_imported(self):
        """Test that embeddings provider can be imported without errors."""
        try:
            from src.ai.providers.embeddings.openai_embeddings_provider import OpenAIEmbeddingsProvider
            assert OpenAIEmbeddingsProvider is not None, "OpenAIEmbeddingsProvider import failed"
        except Exception as e:
            pytest.fail(f"Failed to import OpenAIEmbeddingsProvider: {str(e)}")

    def test_api_configuration_consistency(self):
        """Test that API configuration is consistent across settings."""
        api_key = os.getenv("OPENAI_API_KEY")
        temperature = os.getenv("OPENAI_TEMPERATURE")
        max_tokens = os.getenv("OPENAI_MAX_TOKENS")
        
        assert api_key, "OPENAI_API_KEY not configured"
        assert temperature is not None, "OPENAI_TEMPERATURE not configured"
        assert max_tokens is not None, "OPENAI_MAX_TOKENS not configured"
        
        # Validate ranges
        temp_float = float(temperature)
        assert 0 <= temp_float <= 2, f"Temperature out of range: {temp_float}"
        
        max_tokens_int = int(max_tokens)
        assert max_tokens_int > 0, f"Max tokens must be positive: {max_tokens_int}"
