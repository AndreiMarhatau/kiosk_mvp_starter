from fastapi.testclient import TestClient

def test_config_fields(client: TestClient):
    r = client.get('/config')
    assert r.status_code == 200
    j = r.json()
    assert 'org_name' in j
    assert 'theme' in j
    assert 'footer_clock_format' in j
    # weather fields present
    assert 'show_weather' in j
    assert 'weather_city' in j
