from fastapi.testclient import TestClient
from app.main import app

def test_internal_auth_and_path_validation(monkeypatch):
    monkeypatch.setenv('ENGINE_TOKEN','internal-secret')
    with TestClient(app) as client:
        assert client.post('/embed',json={'text':'test'}).status_code==401
        response=client.post('/process',headers={'Authorization':'Bearer internal-secret'},json={'storage_key':'../../etc/passwd'})
        assert response.status_code==422
        assert client.post('/config',headers={'Authorization':'Bearer internal-secret'},json={}).status_code==200
