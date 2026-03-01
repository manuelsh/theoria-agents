"""Provider-agnostic LLM client using LiteLLM."""

import asyncio
from typing import Any

import litellm


class LLMClient:
    """Async LLM client with retry logic and provider abstraction."""

    def __init__(
        self,
        default_model: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.default_model = default_model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        """Send a completion request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Model identifier. Uses default_model if not specified.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens in response.
            **kwargs: Additional arguments passed to litellm.

        Returns:
            The assistant's response text.

        Raises:
            Exception: If all retries fail.
        """
        model = model or self.default_model
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    await asyncio.sleep(delay)

        raise last_error or Exception("LLM request failed")

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Send a completion request expecting JSON response.

        Adds instruction to respond in JSON format.
        """
        # Add JSON instruction to system message or create one
        json_messages = list(messages)
        if json_messages and json_messages[0]["role"] == "system":
            json_messages[0] = {
                "role": "system",
                "content": json_messages[0]["content"]
                + "\n\nRespond with valid JSON only, no markdown code blocks.",
            }
        else:
            json_messages.insert(
                0,
                {
                    "role": "system",
                    "content": "Respond with valid JSON only, no markdown code blocks.",
                },
            )

        return await self.complete(
            json_messages,
            model=model,
            temperature=0.3,  # Lower temperature for structured output
            **kwargs,
        )
