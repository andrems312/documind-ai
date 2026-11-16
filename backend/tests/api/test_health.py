async def test_health_reports_degraded_without_database(client) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] == "error"
    assert body["checks"]["openrouter"] in {"configured", "missing"}
    assert response.headers["x-request-id"]


async def test_unknown_route_uses_error_envelope(client) -> None:
    response = await client.get("/api/v1/nao-existe")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
