from fastapi.testclient import TestClient

def test_create_user(client: TestClient):
    response = client.post(
        "/api/v1/users/",
        json={"email": "test@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

def test_read_users(client: TestClient):
    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_read_user(client: TestClient):
    # First create a user
    create_response = client.post(
        "/api/v1/users/",
        json={"email": "test2@example.com"},
    )
    user_id = create_response.json()["id"]
    
    # Then read it
    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["email"] == "test2@example.com" 