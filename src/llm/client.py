"""LLM client with streaming support, retry logic, and token tracking.

Provides a unified interface for LLM inference with:
- Automatic retry with exponential backoff
- Streaming response support
- Token usage tracking for cost monitoring
- Structured output parsing
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import get_settings
from src.core.exceptions import LLMError
from src.core.logging import get_logger
from src.models.schemas import TokenUsage
from src.monitoring.metrics import (
    LLM_REQUEST_LATENCY,
    LLM_TOKEN_USAGE,
    LLM_REQUEST_ERRORS,
)

logger = get_logger(__name__)

# Approximate pricing per 1K tokens (GPT-4 Turbo as of 2024)
PRICING = {
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}


class LLMClient:
    """Async OpenAI LLM client with observability."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        self._model = settings.openai_model
        self._max_tokens = settings.max_token_output

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
    ) -> tuple[str, TokenUsage]:
        """Generate a completion from the LLM.

        Args:
            messages: Chat messages in OpenAI format.
            temperature: Sampling temperature (lower = more deterministic).
            max_tokens: Max output tokens (defaults to config).
            response_format: Optional structured output format.

        Returns:
            Tuple of (response_text, token_usage).

        Raises:
            LLMError: If the API call fails after retries.
        """
        start = time.perf_counter()
        max_tokens = max_tokens or self._max_tokens

        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = await self._client.chat.completions.create(**kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Track metrics
            LLM_REQUEST_LATENCY.observe(elapsed_ms / 1000)

            content = response.choices[0].message.content or ""
            usage = self._extract_usage(response)

            LLM_TOKEN_USAGE.labels(type="prompt").inc(usage.prompt_tokens)
            LLM_TOKEN_USAGE.labels(type="completion").inc(usage.completion_tokens)

            logger.info(
                "llm_generation_complete",
                model=self._model,
                latency_ms=round(elapsed_ms, 2),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )

            return content, usage

        except Exception as e:
            LLM_REQUEST_ERRORS.inc()
            raise LLMError(f"LLM generation failed: {e}") from e

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response tokens.

        Yields individual text chunks as they arrive from the API.
        """
        max_tokens = max_tokens or self._max_tokens

        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            LLM_REQUEST_ERRORS.inc()
            raise LLMError(f"LLM streaming failed: {e}") from e

    def _extract_usage(self, response: Any) -> TokenUsage:
        """Extract token usage and estimate cost."""
        usage = response.usage
        if not usage:
            return TokenUsage()

        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens

        # Estimate cost
        pricing = PRICING.get(self._model, PRICING["gpt-4-turbo-preview"])
        cost = (
            (prompt_tokens / 1000) * pricing["input"]
            + (completion_tokens / 1000) * pricing["output"]
        )

        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=round(cost, 6),
        )

    @property
    def model_name(self) -> str:
        return self._model
