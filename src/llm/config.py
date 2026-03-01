"""Configuration loader for LLM models and settings."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def load_config() -> dict[str, Any]:
    """Load configuration from .env and settings.yaml.

    Returns:
        Combined configuration dict with environment variables and YAML settings.
    """
    load_dotenv()

    config: dict[str, Any] = {
        "theoria_dataset_path": os.getenv("THEORIA_DATASET_PATH"),
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "models": {
            "fast": os.getenv("BEDROCK_MODEL_FAST"),
            "best": os.getenv("BEDROCK_MODEL_BEST"),
        },
    }

    # Load settings.yaml if it exists
    settings_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    if settings_path.exists():
        with open(settings_path) as f:
            yaml_config = yaml.safe_load(f) or {}
            config["agent_models"] = yaml_config.get("agent_models", {})
            config["web_search"] = yaml_config.get("web_search", {})
            config["reviewer"] = yaml_config.get("reviewer", {})

    return config


def get_model(agent_name: str, config: dict[str, Any] | None = None) -> str:
    """Get the model identifier for a specific agent.

    Args:
        agent_name: Name of the agent (researcher, derivation, verifier, assembler, reviewer).
        config: Configuration dict. Loads from env/yaml if not provided.

    Returns:
        Model identifier string (ARN or model ID).

    Raises:
        ValueError: If model configuration is missing.
    """
    if config is None:
        config = load_config()

    # Get which model tier to use (fast/best)
    agent_models = config.get("agent_models", {})
    model_tier = agent_models.get(agent_name, "best")

    # Get the actual model identifier
    model = config.get("models", {}).get(model_tier)

    if not model:
        raise ValueError(
            f"Model not configured for agent '{agent_name}'. "
            f"Set BEDROCK_MODEL_{model_tier.upper()} in .env file."
        )

    # Format for LiteLLM if it's a Bedrock ARN or model ID
    if model.startswith("arn:aws:bedrock") or "anthropic" in model.lower():
        if not model.startswith("bedrock/"):
            model = f"bedrock/{model}"

    return model


def get_dataset_path(config: dict[str, Any] | None = None) -> Path:
    """Get the path to the theoria-dataset.

    Args:
        config: Configuration dict. Loads from env if not provided.

    Returns:
        Path to theoria-dataset directory.

    Raises:
        ValueError: If THEORIA_DATASET_PATH is not set or doesn't exist.
    """
    if config is None:
        config = load_config()

    dataset_path = config.get("theoria_dataset_path")

    if not dataset_path:
        raise ValueError(
            "THEORIA_DATASET_PATH not set. Add it to your .env file."
        )

    path = Path(dataset_path)
    if not path.exists():
        raise ValueError(f"Dataset path does not exist: {path}")

    return path
