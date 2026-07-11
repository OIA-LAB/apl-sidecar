import http.client
import json
import threading

import pytest

from cli.apl import main
from relay.openai_proxy import HOST, create_server, handle_chat


def test_completion_shape_and_evidence_without_prompt_echo():
    secret = "do-not-echo-this-secret"
    code, result = handle_chat({"model": "apl-mock-a", "messages": [{"content": secret}]})
    assert code == 200
    assert result["object"] == "chat.completion"
    assert result["choices"][0]["message"]["role"] == "assistant"
    assert result["apl"] == {"mode": "offline-mock", "provider_id": "mock_provider_a"}
    assert secret not in json.dumps(result)


@pytest.mark.parametrize("body, phrase", [
    ({"model": "missing", "messages": [{"content": "x"}]}, "unknown model"),
    ({"model": "apl-mock-a", "stream": True, "messages": [{"content": "x"}]}, "streaming"),
    ({"model": "apl-mock-a", "messages": "bad"}, "messages"),
    ({"model": "apl-mock-a", "messages": [{}]}, "string content"),
])
def test_invalid_chat_requests(body, phrase):
    code, result = handle_chat(body)
    assert code == 400
    assert phrase in result["error"]["message"]


def test_server_loopback_models_and_invalid_json():
    server = create_server(0)
    assert server.server_address[0] == HOST
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = http.client.HTTPConnection(HOST, server.server_port)
        client.request("GET", "/v1/models")
        response = client.getresponse()
        assert response.status == 200
        assert len(json.loads(response.read())["data"]) == 2
        client.request("POST", "/v1/chat/completions", "not-json",
                       {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_cli_entry_point_smoke(capsys):
    assert main([]) == 2
    assert "APL Sidecar CLI" in capsys.readouterr().out

