from __future__ import annotations

import json
from typing import Any
from urllib import parse
from urllib import request


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
MAX_PROVIDER_REQUEST_BYTES = 256 * 1024
MAX_PROVIDER_RESPONSE_BYTES = 1024 * 1024
MIN_PROVIDER_TIMEOUT_SECONDS = 5
MAX_PROVIDER_TIMEOUT_SECONDS = 60


class PromptWorkbenchOpenAIProviderError(RuntimeError):
    pass


def bounded_provider_timeout(value: object, *, default: int = 20) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        timeout = default
    return max(MIN_PROVIDER_TIMEOUT_SECONDS, min(timeout, MAX_PROVIDER_TIMEOUT_SECONDS))


def _validate_http_url_structure(url: str) -> str:
    candidate = str(url or "").strip()
    if not candidate or any(character.isspace() for character in candidate):
        raise PromptWorkbenchOpenAIProviderError("Provider endpoint must be a valid HTTP(S) URL.")
    try:
        parsed = parse.urlsplit(candidate)
        hostname = parsed.hostname
    except ValueError as exc:
        raise PromptWorkbenchOpenAIProviderError("Provider endpoint must be a valid HTTP(S) URL.") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise PromptWorkbenchOpenAIProviderError("Provider endpoint must use HTTP or HTTPS and include a host.")
    if parsed.username is not None or parsed.password is not None:
        raise PromptWorkbenchOpenAIProviderError("Provider endpoint URL credentials are not allowed.")
    if parsed.fragment:
        raise PromptWorkbenchOpenAIProviderError("Provider endpoint fragments are not allowed.")
    return candidate


def validate_provider_endpoint(
    raw_url: object,
    *,
    default_url: str,
    allow_custom_endpoint: bool,
) -> str:
    canonical_default = _validate_http_url_structure(default_url).rstrip("/")
    candidate = _validate_http_url_structure(str(raw_url or "").strip() or canonical_default).rstrip("/")
    if candidate != canonical_default and allow_custom_endpoint is not True:
        raise PromptWorkbenchOpenAIProviderError(
            "Custom provider endpoints require allow_custom_endpoint=true."
        )
    # This proportional local-product check does not provide DNS-rebinding or enterprise egress isolation.
    return candidate


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
    _validate_http_url_structure(url)
    if data is not None and len(data) > MAX_PROVIDER_REQUEST_BYTES:
        raise PromptWorkbenchOpenAIProviderError(
            f"Provider request body must be at most {MAX_PROVIDER_REQUEST_BYTES} bytes."
        )
    req = request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    try:
        with request.urlopen(req, timeout=bounded_provider_timeout(timeout)) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            response_bytes = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
    except PromptWorkbenchOpenAIProviderError:
        raise
    except Exception as exc:
        raise PromptWorkbenchOpenAIProviderError(
            f"Provider request failed ({type(exc).__name__})."
        ) from exc
    if len(response_bytes) > MAX_PROVIDER_RESPONSE_BYTES:
        raise PromptWorkbenchOpenAIProviderError(
            f"Provider response body must be at most {MAX_PROVIDER_RESPONSE_BYTES} bytes."
        )
    try:
        payload = json.loads(response_bytes.decode(charset))
    except (LookupError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptWorkbenchOpenAIProviderError("Provider response was not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise PromptWorkbenchOpenAIProviderError("Provider response JSON must be an object.")
    return payload


def openai_chat_completion(
    *,
    provider_config: dict[str, Any],
    messages: list[dict[str, str]],
    temperature: float = 0.2,
) -> str:
    api_key = str(provider_config.get("api_key", "")).strip()
    base_url = validate_provider_endpoint(
        provider_config.get("base_url"),
        default_url=DEFAULT_OPENAI_BASE_URL,
        allow_custom_endpoint=provider_config.get("allow_custom_endpoint") is True,
    )
    model = str(provider_config.get("model", "")).strip()
    timeout_seconds = bounded_provider_timeout(provider_config.get("timeout_seconds", 20))
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
