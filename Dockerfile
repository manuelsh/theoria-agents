FROM python:3.11-slim

# Copy both repositories from parent context
WORKDIR /workspace
COPY theoria-agents/ /workspace/theoria-agents/
COPY theoria-dataset/ /workspace/theoria-dataset/

# Work in theoria-agents
WORKDIR /workspace/theoria-agents

# Install dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Override .env to point to Docker paths
RUN sed -i 's|THEORIA_DATASET_PATH=.*|THEORIA_DATASET_PATH=/workspace/theoria-dataset|' .env

# Default: run unit tests only (no integration)
CMD ["pytest", "-v", "-m", "not integration"]
