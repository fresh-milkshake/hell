import pytest
from fastapi.testclient import TestClient
from app.hell_gate import app

client = TestClient(app)


@pytest.fixture
def test_create_daemon():
    response = client.get("/daemons/")
    assert response.status_code == 200
    assert response.json() == {"daemons": []}
