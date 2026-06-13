import pytest
from fastapi.testclient import TestClient
from main import app
import os

# Устанавливаем переменные окружения для тестов, если они не заданы
os.environ["INTAKE_SERVICE_URL"] = "http://intake-agent:8001"
os.environ["LAWYER_SERVICE_URL"] = "http://lawyer-service:8002"

@pytest.fixture
def client():
    """Фикстура для FastAPI TestClient"""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_env():
    """Фикстура для проверки переменных окружения (опционально)"""
    return {
        "INTAKE_SERVICE_URL": os.getenv("INTAKE_SERVICE_URL"),
        "LAWYER_SERVICE_URL": os.getenv("LAWYER_SERVICE_URL")
    }
