import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio  # Mark the test as async
async def test_health_check(client: TestClient):
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_status"] in ["healthy", "unhealthy"]
