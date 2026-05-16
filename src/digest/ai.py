"""AI provider adapters used by the digest workflow."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
import urllib.error
import urllib.request
from typing import Protocol


class AIProviderError(RuntimeError):
    """Raised when an AI provider cannot return usable output."""


class AIProvider(Protocol):
    """Small provider interface so the workflow is not tied to one backend."""

    def complete(self, prompt: str) -> str:
        """Return a text completion for the supplied prompt."""


@dataclass(frozen=True)
class LMStudioConfig:
    """Configuration for an OpenAI-compatible LM Studio endpoint."""

    base_url: str = "http://127.0.0.1:1234/v1"
    model: str = "local-model"
    timeout_seconds: float = 60.0
    retries: int = 1
    max_tokens: int = 1400


class LMStudioProvider:
    """OpenAI-compatible chat completion client for LM Studio."""

    def __init__(self, config: LMStudioConfig | None = None) -> None:
        self.config = config or LMStudioConfig()

    def complete(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.config.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert Vietnamese technical editor. "
                            "Return only the requested content."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": self.config.max_tokens,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.config.retries + 1):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.config.timeout_seconds,
                ) as response:
                    body = json.loads(response.read().decode("utf-8"))
                return _extract_completion(body)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError) as exc:
                last_error = exc
                if attempt < self.config.retries:
                    time.sleep(0.2 * (attempt + 1))
                    continue
                break

        raise AIProviderError(
            "Không thể gọi LM Studio. Hãy kiểm tra server local, model đã load, "
            f"và endpoint `{self.config.base_url}`."
        ) from last_error


def _extract_completion(payload: dict[str, object]) -> str:
    choices = payload["choices"]
    if not isinstance(choices, list) or not choices:
        raise KeyError("choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise TypeError("choices[0]")
    message = first["message"]
    if not isinstance(message, dict):
        raise TypeError("message")
    content = message["content"]
    if not isinstance(content, str) or not content.strip():
        raise TypeError("content")
    return content.strip()
