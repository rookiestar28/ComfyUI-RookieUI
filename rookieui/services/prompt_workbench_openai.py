from __future__ import annotations

import json
from typing import Any
from urllib import request


class PromptWorkbenchOpenAIProviderError(RuntimeError):
    pass


def openai_headers(api_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def urlopen_json(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> dict[str, Any]:
    req = request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    with request.urlopen(req, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def openai_chat_completion(
    *,
    provider_config: dict[str, Any],
    messages: list[dict[str, str]],
    temperature: float = 0.2,
) -> str:
    api_key = str(provider_config.get("api_key", "")).strip()
    base_url = str(provider_config.get("base_url", "")).strip() or "https://api.openai.com/v1"
    model = str(provider_config.get("model", "")).strip()
    timeout_seconds = int(provider_config.get("timeout_seconds", 20) or 20)
    if not api_key or not model:
        raise PromptWorkbenchOpenAIProviderError("OpenAI-compatible execution requires api_key and model.")

    response_payload = urlopen_json(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            },
            ensure_ascii=True,
        ).encode("utf-8"),
        headers=openai_headers(api_key),
        timeout=timeout_seconds,
    )
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise PromptWorkbenchOpenAIProviderError("OpenAI-compatible response did not include choices.")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = str(message.get("content", "")).strip()
    if not content:
        raise PromptWorkbenchOpenAIProviderError("OpenAI-compatible response returned empty content.")
    return content
