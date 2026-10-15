"""Service guards, tested with the model call stubbed out (no API spend, no database)."""
from fastapi.testclient import TestClient

import app.server as server


def _client(monkeypatch, per_ip=2, total=3):
    monkeypatch.setattr(server, "PER_IP", per_ip)
    monkeypatch.setattr(server, "TOTAL", total)
    server._counts.update(total=0, ip={})
    monkeypatch.setattr(server, "_answer", lambda q: {"answer": "ok [Player, 2023/24]", "sources": ["Player, 2023/24"], "route": "stats"})
    return TestClient(server.app)


def test_answer_shape(monkeypatch):
    r = _client(monkeypatch).post("/ask", json={"question": "who scored most?"})
    assert r.status_code == 200
    assert r.json()["sources"] == ["Player, 2023/24"]


def test_empty_and_long_questions_rejected(monkeypatch):
    c = _client(monkeypatch)
    assert c.post("/ask", json={"question": "  "}).status_code == 400
    assert c.post("/ask", json={"question": "x" * (server.MAX_CHARS + 1)}).status_code == 400


def test_per_ip_limit(monkeypatch):
    c = _client(monkeypatch, per_ip=2, total=50)
    h = {"x-forwarded-for": "1.2.3.4"}
    assert c.post("/ask", json={"question": "a"}, headers=h).status_code == 200
    assert c.post("/ask", json={"question": "a"}, headers=h).status_code == 200
    assert c.post("/ask", json={"question": "a"}, headers=h).status_code == 429
    assert c.post("/ask", json={"question": "a"}, headers={"x-forwarded-for": "5.6.7.8"}).status_code == 200


def test_total_limit(monkeypatch):
    c = _client(monkeypatch, per_ip=50, total=2)
    for i in range(2):
        assert c.post("/ask", json={"question": "a"}, headers={"x-forwarded-for": f"9.9.9.{i}"}).status_code == 200
    assert c.post("/ask", json={"question": "a"}, headers={"x-forwarded-for": "9.9.9.9"}).status_code == 429


def test_home_page(monkeypatch):
    assert "scouting assistant" in _client(monkeypatch).get("/").text


def test_backend_failure_is_a_clean_502(monkeypatch):
    c = _client(monkeypatch)
    def boom(q):
        raise RuntimeError("credit balance too low")
    monkeypatch.setattr(server, "_answer", boom)
    r = c.post("/ask", json={"question": "a"})
    assert r.status_code == 502
    assert "credit" not in r.json()["detail"]
