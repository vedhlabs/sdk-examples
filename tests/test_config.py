import io
import json

from example_support import config


def test_given_admin_api_when_namespace_is_created_then_immutable_id_is_returned(
    monkeypatch,
):
    captured = {}

    def open_request(call, *, timeout):
        captured["url"] = call.full_url
        captured["method"] = call.method
        captured["body"] = json.loads(call.data)
        captured["authorization"] = call.get_header("Authorization")
        captured["timeout"] = timeout
        return io.BytesIO(b'{"namespace":{"id":"ns_0123456789abcdef01234567"}}')

    monkeypatch.setenv("AGA_URL", "http://aga.test/")
    monkeypatch.setenv("AGA_API_KEY", "admin-token")
    monkeypatch.setattr(config.request, "urlopen", open_request)

    namespace_id = config.create_namespace("Example smoke")

    assert namespace_id == "ns_0123456789abcdef01234567"
    assert captured == {
        "url": "http://aga.test/api/namespaces",
        "method": "POST",
        "body": {"name": "Example smoke"},
        "authorization": "Bearer admin-token",
        "timeout": 10,
    }
