from fastapi.testclient import TestClient

def test_update_settings_weather(client: TestClient):
    # need auth cookie, simulate by skipping auth via monkeypatch? For smoke, check 401 without auth
    r = client.put('/admin/settings', json={'show_weather': True, 'weather_city': 'Минск'})
    assert r.status_code in (401, 403)


def test_update_theme_requires_auth(client: TestClient):
    r = client.put('/admin/theme', json={'bg': '#ffffff'})
    assert r.status_code in (401, 403)
