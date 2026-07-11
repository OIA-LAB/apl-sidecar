"""Minimal OpenAI-compatible, loopback-only offline mock proxy."""
from __future__ import annotations

import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from adapters.base import ProviderRequest
from adapters.mock import default_registry

HOST = "127.0.0.1"
MAX_BODY_BYTES = 64 * 1024
MODELS = {"apl-mock-a": "mock_provider_a", "apl-mock-b": "mock_provider_b"}


def _error(message: str) -> dict[str, Any]:
    return {"error": {"message": message, "type": "invalid_request_error"}}


def handle_chat(body: Any) -> tuple[int, dict[str, Any]]:
    if not isinstance(body, dict):
        return 400, _error("request body must be a JSON object")
    model = body.get("model")
    if model not in MODELS:
        return 400, _error("unknown model")
    if body.get("stream"):
        return 400, _error("streaming is not supported")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return 400, _error("messages must be a non-empty array")
    if any(not isinstance(m, dict) or not isinstance(m.get("content"), str) for m in messages):
        return 400, _error("each message must contain string content")
    provider_id = MODELS[model]
    response = default_registry().get(provider_id).complete(
        ProviderRequest(prompt="\n".join(m["content"] for m in messages), model=model)
    )
    return 200, {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": response.text},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "apl": {"mode": "offline-mock", "provider_id": provider_id},
    }


class OpenAIProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/models":
            self._send(404, _error("not found"))
            return
        data = [{"id": model, "object": "model", "owned_by": "apl-sidecar"} for model in MODELS]
        self._send(200, {"object": "list", "data": data})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send(404, _error("not found"))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, _error("invalid content length"))
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send(413, _error("request body too large or empty"))
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(400, _error("invalid JSON"))
            return
        self._send(*handle_chat(body))

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def create_server(port: int = 8793) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((HOST, port), OpenAIProxyHandler)


def serve(port: int = 8793) -> int:
    server = create_server(port)
    print(f"APL offline mock proxy: http://{HOST}:{server.server_port}/v1")
    print("Loopback only. Prompts are not logged. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
