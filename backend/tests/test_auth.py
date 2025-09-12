from fastapi.testclient import TestClient

def test_login_fail(client: TestClient):
    r = client.post('/auth/login', data={'username':'nouser','password':'no'}, allow_redirects=False)
    # FastAPI returns 200 with template on failure; ensure not redirect to /admin
    assert r.status_code in (200, 401)

