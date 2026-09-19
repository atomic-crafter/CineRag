import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DATABASE_URL", "postgresql://rag:ragpass@localhost:5432/ragdb")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("ZAI_API_KEY", "unused-in-tests")
os.environ.setdefault("ZAI_BASE_URL", "http://unused.invalid")

import pytest
from fastapi.testclient import TestClient

import app as app_module


@pytest.fixture(scope="session")
def client():
    with TestClient(app_module.app) as c:
        yield c
