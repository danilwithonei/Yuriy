import os
import warnings

os.environ["TESTING"] = "1"

warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")
warnings.filterwarnings("ignore", message="Couldn't parse", category=UserWarning, module="coverage")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from typing import Dict

from database import engine
from main import app
from models import Lawyer
from auth import hash_password, create_token, get_lawyer_by_email

INTAKE_URL = os.getenv("INTAKE_SERVICE_URL", "http://intake-agent:8001")
LAWYER_URL = os.getenv("LAWYER_SERVICE_URL", "http://lawyer-service:8002")

TEST_LAWYERS = [
    ("lawyer_a@test.com", "Lawyer A", "pass1234"),
    ("lawyer_b@test.com", "Lawyer B", "pass5678"),
]

@pytest.fixture(scope="session", autouse=True)
def test_db():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(scope="session")
def lawyers() -> Dict[str, str]:
    ids = {}
    tokens = {}
    for email, name, pw in TEST_LAWYERS:
        with Session(engine) as session:
            existing = get_lawyer_by_email(session, email)
            if existing:
                lid = existing.id
            else:
                lawyer = Lawyer(email=email, name=name, password_hash=hash_password(pw))
                session.add(lawyer)
                session.commit()
                session.refresh(lawyer)
                lid = lawyer.id
        ids[email] = lid
        tokens[email] = create_token(lid)
    return {"ids": ids, "tokens": tokens}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(lawyers):
    return {"Authorization": f"Bearer {lawyers['tokens']['lawyer_a@test.com']}"}

@pytest.fixture
def auth_headers_b(lawyers):
    return {"Authorization": f"Bearer {lawyers['tokens']['lawyer_b@test.com']}"}