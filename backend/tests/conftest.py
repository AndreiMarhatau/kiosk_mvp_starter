import os
import tempfile
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('SECURE_COOKIES', '0')

from app.main import app, SessionLocal, Base, engine

@pytest.fixture(scope='session', autouse=True)
def _prepare_db():
    # Ensure tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    yield

@pytest.fixture()
def client():
    return TestClient(app)
