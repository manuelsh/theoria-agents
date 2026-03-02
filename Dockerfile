FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md AGENTS.md ./
COPY src/ src/
COPY tests/ tests/
COPY config/ config/

RUN pip install --no-cache-dir -e ".[dev]"

# Default: run unit tests only (no integration)
# For integration tests, run with:
#   docker run --rm \
#     -v ~/.aws:/root/.aws:ro \
#     -v ./.env:/app/.env:ro \
#     -v /path/to/theoria-dataset:/theoria-dataset:ro \
#     -e AWS_PROFILE=claude \
#     theoria-agents-test pytest -v -m integration
CMD ["pytest", "-v", "-m", "not integration"]
