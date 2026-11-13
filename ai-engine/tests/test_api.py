from fastapi.testclient import TestClient
from app.main import app

def test_internal_auth_and_path_validation(monkeypatch):
    monkeypatch.setenv('ENGINE_TOKEN','internal-secret')
    with TestClient(app) as client:
        assert client.post('/embed',json={'text':'test'}).status_code==401
        response=client.post('/process',headers={'Authorization':'Bearer internal-secret'},json={'storage_key':'../../etc/passwd'})
        assert response.status_code==422
        assert client.post('/config',headers={'Authorization':'Bearer internal-secret'},json={}).status_code==200

def test_embedding_identity_separates_lexical_and_semantic(monkeypatch):
    import json
    from pathlib import Path
    from app.retrieval import embedding_version, REVISION
    lock=json.loads((Path(__file__).parents[1]/'model.lock.json').read_text())
    assert lock['revision']==REVISION
    monkeypatch.setenv('EMBEDDING_MODE','lexical')
    assert embedding_version()=='lexical-sha256-v1'
    monkeypatch.setenv('EMBEDDING_MODE','semantic')
    assert embedding_version()==lock['model']+'@'+lock['revision']
