from fastapi.testclient import TestClient

from sheets_json_gateway import app as app_module

client = TestClient(app_module.app)
BODY = {"sheet_id": "abc", "ranges": ["A1:B2"]}


def _fake_read(**_kwargs):
    return [{"range": "A1:B2", "values": [["k", "v"]]}]


def test_healthz_is_open(monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", "s3cret")
    assert client.get("/healthz").status_code == 200


def test_no_key_configured_allows_requests(monkeypatch):
    monkeypatch.delenv("GATEWAY_API_KEY", raising=False)
    monkeypatch.setattr(app_module, "read_ranges", _fake_read)
    assert client.post("/v1/read", json=BODY).status_code == 200


def test_key_configured_rejects_missing_or_wrong_key(monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", "s3cret")
    monkeypatch.setattr(app_module, "read_ranges", _fake_read)
    assert client.post("/v1/read", json=BODY).status_code == 401
    assert client.post("/v1/read", json=BODY, headers={"X-API-Key": "nope"}).status_code == 401
    assert client.post("/v1/write", json={"sheet_id": "abc", "updates": [{"range": "A1", "values": [["x"]]}]}).status_code == 401


def test_key_configured_accepts_correct_key(monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", "s3cret")
    monkeypatch.setattr(app_module, "read_ranges", _fake_read)
    assert client.post("/v1/read", json=BODY, headers={"X-API-Key": "s3cret"}).status_code == 200
