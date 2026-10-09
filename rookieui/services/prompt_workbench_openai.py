from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import http.client
import ipaddress
import json
import socket
from collections.abc import Iterator
from typing import Any
from urllib import parse
from urllib import request


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MYMEMORY_BASE_URL = "https://api.mymemory.translated.net/get"
_PROVIDER_BASE_URLS = frozenset({DEFAULT_OPENAI_BASE_URL, DEFAULT_MYMEMORY_BASE_URL})
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
    # SECURITY: API/import payloads control both URL and opt-in; the flag cannot authorize egress.
    if canonical_default not in _PROVIDER_BASE_URLS or candidate != canonical_default:
        raise PromptWorkbenchOpenAIProviderError(
            "Custom provider endpoints are not supported. Restore the official provider HTTPS endpoint."
        )
    return candidate


def validate_prompt_workbench_provider_config(config: dict[str, Any]) -> None:
    for surface in ("translation", "ai_assist"):
        settings = config.get(surface, {})
        providers = settings.get("providers", {}) if isinstance(settings, dict) else {}
        if not isinstance(providers, dict):
            continue
        for provider_id, default_url in (
            ("openai", DEFAULT_OPENAI_BASE_URL),
            ("mymemory_free", DEFAULT_MYMEMORY_BASE_URL),
        ):
            provider_config = providers.get(provider_id)
            if not isinstance(provider_config, dict):
                continue
            try:
                validate_provider_endpoint(
                    provider_config.get("base_url"),
                    default_url=default_url,
                    allow_custom_endpoint=False,
                )
            except PromptWorkbenchOpenAIProviderError as exc:
                raise ValueError(str(exc)) from exc


def _validate_provider_request(req: request.Request) -> tuple[str, str]:
    url = _validate_http_url_structure(req.full_url)
    parsed = parse.urlsplit(url)
    hostname = parsed.hostname or ""
    method = req.get_method()
    is_openai = (
        parsed.netloc == "api.openai.com"
        and parsed.path == "/v1/chat/completions"
        and method == "POST"
        and not parsed.query
    )
    is_mymemory = (
        parsed.netloc == "api.mymemory.translated.net"
        and parsed.path == "/get"
        and method == "GET"
    )
    if parsed.scheme != "https" or not (is_openai or is_mymemory):
        raise PromptWorkbenchOpenAIProviderError("Provider request destination is not approved.")
    if len(url.encode("utf-8")) > MAX_PROVIDER_REQUEST_BYTES:
        raise PromptWorkbenchOpenAIProviderError("Provider request URL exceeds the size limit.")
    if is_mymemory:
        query = parse.parse_qsl(parsed.query, keep_blank_values=True)
        keys = [key for key, _ in query]
        if set(keys) - {"q", "langpair", "de"} or len(keys) != len(set(keys)) or not {"q", "langpair"} <= set(keys):
            raise PromptWorkbenchOpenAIProviderError("MyMemory request query is not approved.")
    for name, _ in req.header_items():
        if name.lower() not in {"content-type", "authorization"} or (
            is_mymemory and name.lower() == "authorization"
        ):
            raise PromptWorkbenchOpenAIProviderError("Provider request headers are not approved.")
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    return hostname, path


@dataclass(frozen=True, slots=True)
class _ProviderAddress:
    family: socket.AddressFamily
    address: str


def _resolve_public_provider_address(hostname: str) -> _ProviderAddress:
    addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    if not addresses:
        raise PromptWorkbenchOpenAIProviderError("Provider DNS returned no usable address.")
    validated: list[_ProviderAddress] = []
    for family, _, _, _, sockaddr in addresses:
        address = str(sockaddr[0])
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise PromptWorkbenchOpenAIProviderError("Provider DNS returned an unsafe address.") from exc
        if (
            family not in {socket.AF_INET, socket.AF_INET6}
            or "%" in address
            or not ip.is_global
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
            or (
                isinstance(ip, ipaddress.IPv6Address)
                and (ip.is_site_local or ip.ipv4_mapped is not None or ip.sixtofour is not None or ip.teredo is not None)
            )
            or (family == socket.AF_INET) != isinstance(ip, ipaddress.IPv4Address)
        ):
            raise PromptWorkbenchOpenAIProviderError("Provider DNS returned an unsafe address.")
        validated.append(_ProviderAddress(socket.AddressFamily(family), str(ip)))
    return validated[0]


class _PinnedProviderHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: _ProviderAddress, *, timeout: int) -> None:
        super().__init__(hostname, port=443, timeout=timeout)
        self._provider_address = address

    def connect(self) -> None:
        if self._tunnel_host:
            raise PromptWorkbenchOpenAIProviderError("Provider proxy tunnels are not supported.")
        address = self._provider_address
        sock = socket.socket(address.family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        try:
            sock.settimeout(self.timeout)
            target = (address.address, 443) if address.family == socket.AF_INET else (address.address, 443, 0, 0)
            # SECURITY: connect only to the validated IP; keep the approved hostname for verified TLS/SNI.
            # Calling super().connect() would resolve again and reopen DNS-rebinding/proxy bypasses.
            sock.connect(target)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


@contextmanager
def _open_provider_response(req: request.Request, *, timeout: int) -> Iterator[http.client.HTTPResponse]:
    hostname, path = _validate_provider_request(req)
    address = _resolve_public_provider_address(hostname)
    connection = _PinnedProviderHTTPSConnection(hostname, address, timeout=timeout)
    try:
        connection.request(req.get_method(), path, body=req.data, headers=dict(req.header_items()))
        with connection.getresponse() as response:
            # SECURITY: never follow Location, including same-host redirects; credentials stay provider-bound.
            if 300 <= response.status < 400:
                raise PromptWorkbenchOpenAIProviderError("Provider redirects are not allowed.")
            if not 200 <= response.status < 300:
                raise PromptWorkbenchOpenAIProviderError(f"Provider returned HTTP {response.status}.")
            yield response
    finally:
        connection.close()


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
    _validate_provider_request(req)
    try:
        with _open_provider_response(req, timeout=bounded_provider_timeout(timeout)) as response:
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
        allow_custom_endpoint=False,
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
