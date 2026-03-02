"""Tests for LLM configuration loading."""

import os
from pathlib import Path
from unittest.mock import patch

import litellm
litellm.drop_params = True  # Bedrock inference profiles don't support all params

import pytest
from src.llm.config import load_config, get_model, get_dataset_path


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_env_variables(self, monkeypatch):
        """Test that environment variables are loaded into config."""
        monkeypatch.setenv("THEORIA_DATASET_PATH", "/test/path")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        monkeypatch.setenv("BEDROCK_MODEL_FAST", "arn:aws:bedrock:fast")
        monkeypatch.setenv("BEDROCK_MODEL_BEST", "arn:aws:bedrock:best")

        config = load_config()

        assert config["theoria_dataset_path"] == "/test/path"
        assert config["aws_region"] == "eu-west-1"
        assert config["models"]["fast"] == "arn:aws:bedrock:fast"
        assert config["models"]["best"] == "arn:aws:bedrock:best"

    def test_default_aws_region(self, monkeypatch):
        """Test that AWS region defaults to us-east-1 when not set."""
        # Mock os.getenv to return None for AWS_REGION
        original_getenv = os.getenv
        def mock_getenv(key, default=None):
            if key == "AWS_REGION":
                return default  # Return the default, which is us-east-1
            return original_getenv(key, default)

        monkeypatch.setattr(os, "getenv", mock_getenv)

        config = load_config()

        assert config["aws_region"] == "us-east-1"


class TestGetModel:
    """Tests for get_model function."""

    def test_returns_bedrock_formatted_arn(self):
        """Test that Bedrock ARNs are formatted with bedrock/ prefix."""
        config = {
            "models": {"best": "arn:aws:bedrock:eu-west-1:123:model/test"},
            "agent_models": {"researcher": "best"},
        }

        model = get_model("researcher", config)

        assert model == "bedrock/arn:aws:bedrock:eu-west-1:123:model/test"

    def test_uses_fast_model_when_configured(self):
        """Test that agents configured for 'fast' use the fast model."""
        config = {
            "models": {
                "fast": "arn:aws:bedrock:eu-west-1:123:fast-model",
                "best": "arn:aws:bedrock:eu-west-1:123:best-model",
            },
            "agent_models": {"assembler": "fast"},
        }

        model = get_model("assembler", config)

        assert "fast-model" in model

    def test_defaults_to_best_model(self):
        """Test that agents default to 'best' model if not configured."""
        config = {
            "models": {"best": "arn:aws:bedrock:eu-west-1:123:best-model"},
            "agent_models": {},
        }

        model = get_model("unknown_agent", config)

        assert "best-model" in model

    def test_raises_error_when_model_not_configured(self):
        """Test that ValueError is raised when model is missing."""
        config = {"models": {}, "agent_models": {}}

        with pytest.raises(ValueError, match="Model not configured"):
            get_model("researcher", config)

    def test_does_not_double_prefix_bedrock(self):
        """Test that already-prefixed models aren't double-prefixed."""
        config = {
            "models": {"best": "bedrock/arn:aws:bedrock:eu-west-1:123:model"},
            "agent_models": {},
        }

        model = get_model("researcher", config)

        assert model == "bedrock/arn:aws:bedrock:eu-west-1:123:model"
        assert not model.startswith("bedrock/bedrock/")


class TestGetDatasetPath:
    """Tests for get_dataset_path function."""

    def test_returns_path_when_configured(self, tmp_path):
        """Test that valid path is returned when configured."""
        config = {"theoria_dataset_path": str(tmp_path)}

        path = get_dataset_path(config)

        assert path == tmp_path

    def test_raises_error_when_not_set(self):
        """Test that ValueError is raised when path is not set."""
        config = {"theoria_dataset_path": None}

        with pytest.raises(ValueError, match="THEORIA_DATASET_PATH not set"):
            get_dataset_path(config)

    def test_raises_error_when_path_does_not_exist(self):
        """Test that ValueError is raised when path doesn't exist."""
        config = {"theoria_dataset_path": "/nonexistent/path"}

        with pytest.raises(ValueError, match="does not exist"):
            get_dataset_path(config)


class TestLLMIntegration:
    """Integration tests that verify real LLM connectivity.

    These tests require a valid .env file with AWS credentials.
    Skip with: pytest -m "not integration"
    """

    @pytest.mark.integration
    def test_env_file_loads_real_config(self):
        """Test that .env file is present and loads valid configuration."""
        config = load_config()

        assert config["theoria_dataset_path"] is not None, "THEORIA_DATASET_PATH not set in .env"
        assert config["models"]["fast"] is not None, "BEDROCK_MODEL_FAST not set in .env"
        assert config["models"]["best"] is not None, "BEDROCK_MODEL_BEST not set in .env"

        # Verify dataset path exists
        dataset_path = get_dataset_path(config)
        assert dataset_path.exists(), f"Dataset path does not exist: {dataset_path}"
        assert (dataset_path / "schemas" / "entry.schema.json").exists(), "entry.schema.json not found"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_connection_fast_model(self):
        """Test that the fast model responds to a simple prompt."""
        from src.llm.client import LLMClient

        config = load_config()
        model = get_model("researcher", config)  # Uses fast model per settings.yaml

        client = LLMClient(default_model=model, max_retries=1)

        response = await client.complete(
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
        )

        assert response is not None
        assert len(response) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_connection_best_model(self):
        """Test that the best model responds to a simple prompt."""
        from src.llm.client import LLMClient

        config = load_config()
        model = get_model("derivation", config)  # Uses best model per settings.yaml

        client = LLMClient(default_model=model, max_retries=1)

        response = await client.complete(
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
        )

        assert response is not None
        assert len(response) > 0
