import pytest
from httpx import Response, ConnectTimeout
from datetime import datetime, timedelta, timezone
from jose import jwt
import os

from auth import SECRET_KEY, ALGORITHM

AUTH_URL = ""

def _expired_token():
    payload = {"sub": "999999", "exp": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def _garbage_token():
    return "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.invalid"

class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/auth/register", json={
            "email": f"fresh_{__import__('uuid').uuid4().hex[:8]}@test.com",
            "name": "Fresh Lawyer",
            "password": "pass1234"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["lawyer"]["email"].startswith("fresh_")
        assert data["lawyer"]["name"] == "Fresh Lawyer"

    def test_register_duplicate_email(self, client):
        client.post("/auth/register", json={
            "email": "dup@test.com",
            "name": "First",
            "password": "pass1234"
        })
        resp = client.post("/auth/register", json={
            "email": "dup@test.com",
            "name": "Second",
            "password": "pass1234"
        })
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        resp = client.post("/auth/register", json={
            "email": "notanemail",
            "name": "Bad Email",
            "password": "pass1234"
        })
        assert resp.status_code == 400
        assert "invalid email" in resp.json()["detail"].lower()

    def test_register_short_password(self, client):
        resp = client.post("/auth/register", json={
            "email": f"shortpwd_{__import__('uuid').uuid4().hex[:8]}@test.com",
            "name": "Short Pwd",
            "password": "ab"
        })
        assert resp.status_code == 400
        assert "4 characters" in resp.json()["detail"].lower()

    def test_register_empty_body(self, client):
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 422

    def test_register_giant_name(self, client):
        resp = client.post("/auth/register", json={
            "email": f"giant_{__import__('uuid').uuid4().hex[:8]}@test.com",
            "name": "X" * 10000,
            "password": "pass1234"
        })
        assert resp.status_code in (200, 400, 413, 422)

class TestLogin:
    def test_login_wrong_password(self, client):
        resp = client.post("/auth/login", json={
            "email": "lawyer_a@test.com",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_login_nonexistent_email(self, client):
        resp = client.post("/auth/login", json={
            "email": "nobody@test.com",
            "password": "pass1234"
        })
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_login_broken_json(self, client):
        resp = client.post("/auth/login", content="not json", headers={"Content-Type": "application/json"})
        assert resp.status_code in (400, 422)

class TestMe:
    def test_me_without_token(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_expired_token(self, client):
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {_expired_token()}"})
        assert resp.status_code == 401

    def test_me_garbage_token(self, client):
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {_garbage_token()}"})
        assert resp.status_code == 401

    def test_me_deleted_lawyer(self, client):
        from sqlmodel import Session
        from database import engine
        from models import Lawyer
        from auth import create_token
        with Session(engine) as session:
            l = Lawyer(email="deleteme@test.com", name="Delete Me", password_hash="x")
            session.add(l)
            session.commit()
            session.refresh(l)
            lid = l.id
            token = create_token(lid)
            session.delete(l)
            session.commit()
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404