import pytest
import respx
from httpx import Response
from fastapi.testclient import TestClient
from main import app

from conftest import INTAKE_URL, LAWYER_URL

CASE_ID = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"

def test_websocket_dashboard_connection(client, lawyers):
    token = lawyers["tokens"]["lawyer_a@test.com"]
    with client.websocket_connect(f"/ws/dashboard?token={token}"):
        pass

@respx.mock
def test_websocket_case_chat_flow(client, auth_headers, respx_mock):
    token = auth_headers["Authorization"].split(" ")[1]
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(return_value=Response(200, json={
        "case": {"id": CASE_ID, "client_id": 1, "lawyer_id": 1, "case_file": "Case Dossier", "title": None, "summary": None},
        "messages": [{"sender_role": "user", "content": "Initial message"}]
    }))
    sse_body = b"data: {\"token\": \"AI Lawyer Answer\"}\n\ndata: {\"done\": true}\n\n"
    respx_mock.post(f"{LAWYER_URL}/analyze").mock(return_value=Response(200, content=sse_body))

    with client.websocket_connect(f"/ws/cases/{CASE_ID}/chat?token={token}") as websocket:
        websocket.send_json({"message": "Hello AI"})
        resp1 = websocket.receive_json()
        assert resp1["type"] == "AI_THINKING"
        # Пропускаем AI_TOKEN, ждём AI_RESPONSE
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "AI_RESPONSE":
                assert msg["content"] == "AI Lawyer Answer"
                break
            assert msg["type"] == "AI_TOKEN"

@respx.mock
def test_websocket_case_isolation(client, auth_headers, respx_mock):
    token = auth_headers["Authorization"].split(" ")[1]
    other_id = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
    for cid in (CASE_ID, other_id):
        respx_mock.get(f"{INTAKE_URL}/case/{cid}").mock(return_value=Response(200, json={
            "case": {"id": cid, "client_id": 1, "lawyer_id": 1, "case_type": "direct", "title": None, "summary": None},
            "messages": []
        }))
    with client.websocket_connect(f"/ws/cases/{CASE_ID}/chat?token={token}") as ws1, \
         client.websocket_connect(f"/ws/cases/{other_id}/chat?token={token}") as ws2:
        from ws_manager import manager
        assert CASE_ID in manager.case_connections
        assert other_id in manager.case_connections
        assert manager.case_connections[CASE_ID] != manager.case_connections[other_id]

@respx.mock
def test_websocket_service_failure(client, auth_headers, respx_mock):
    token = auth_headers["Authorization"].split(" ")[1]
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(return_value=Response(200, json={
        "case": {"id": CASE_ID, "client_id": 1, "lawyer_id": 1, "case_file": "Dossier", "title": None, "summary": None},
        "messages": []
    }))
    respx_mock.post(f"{LAWYER_URL}/analyze").mock(return_value=Response(500))

    with client.websocket_connect(f"/ws/cases/{CASE_ID}/chat?token={token}") as websocket:
        websocket.send_json({"message": "Trigger error"})
        websocket.receive_json()
        resp = websocket.receive_json()
        assert "error" in resp
        assert "Lawyer Assistant Service error" in resp["error"]

@respx.mock
def test_websocket_invalid_json(client, auth_headers, respx_mock):
    token = auth_headers["Authorization"].split(" ")[1]
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(return_value=Response(200, json={
        "case": {"id": CASE_ID, "client_id": 1, "lawyer_id": 1, "case_file": "Dossier", "title": None, "summary": None},
        "messages": []
    }))
    with client.websocket_connect(f"/ws/cases/{CASE_ID}/chat?token={token}") as websocket:
        websocket.send_text("not a json")
        resp = websocket.receive_json()
        assert "error" in resp
        assert resp["error"] == "Invalid JSON format"