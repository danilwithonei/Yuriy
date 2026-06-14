import pytest
import respx
import json
from httpx import Response
from fastapi.testclient import TestClient
from main import app

INTAKE_URL = "http://intake-agent:8001"
LAWYER_URL = "http://lawyer-service:8002"

def test_websocket_dashboard_connection(client):
    """Проверка подключения к общему дашборду"""
    with client.websocket_connect("/ws/dashboard") as websocket:
        # Просто проверяем, что соединение установлено
        assert True

@respx.mock
def test_websocket_case_chat_flow(client, respx_mock):
    """Проверка полного цикла чата в WebSocket"""
    case_id = 1
    respx_mock.get(f"{INTAKE_URL}/case/{case_id}").mock(return_value=Response(200, json={
        "case": {"id": case_id, "case_file": "Case Dossier"},
        "messages": [{"sender_role": "user", "content": "Initial message"}]
    }))
    respx_mock.post(f"{LAWYER_URL}/analyze").mock(return_value=Response(200, json={"response": "AI Lawyer Answer"}))

    with client.websocket_connect(f"/ws/cases/{case_id}/chat") as websocket:
        # Отправляем сообщение
        websocket.send_json({"message": "Hello AI"})
        
        # 1. Должны получить статус "Мысли"
        resp1 = websocket.receive_json()
        assert resp1["type"] == "AI_THINKING"
        
        # 2. Должны получить ответ от ИИ
        resp2 = websocket.receive_json()
        assert resp2["type"] == "AI_RESPONSE"
        assert resp2["content"] == "AI Lawyer Answer"

def test_websocket_case_isolation(client):
    """Злой тест: Проверка изоляции чатов (сообщения не должны течь в другие дела)"""
    with client.websocket_connect("/ws/cases/1/chat") as ws1, \
         client.websocket_connect("/ws/cases/2/chat") as ws2:
        
        # Мы не можем легко вызвать send_case_message извне без триггера, 
        # но мы можем проверить, что менеджер хранит их раздельно.
        from ws_manager import manager
        assert 1 in manager.case_connections
        assert 2 in manager.case_connections
        assert manager.case_connections[1] != manager.case_connections[2]

@respx.mock
def test_websocket_service_failure(client, respx_mock):
    """Злой тест: Lawyer Service падает во время чата"""
    case_id = 1
    respx_mock.get(f"{INTAKE_URL}/case/{case_id}").mock(return_value=Response(200, json={
        "case": {"id": case_id, "case_file": "Dossier"},
        "messages": []
    }))
    respx_mock.post(f"{LAWYER_URL}/analyze").mock(return_value=Response(500))

    with client.websocket_connect(f"/ws/cases/{case_id}/chat") as websocket:
        websocket.send_json({"message": "Trigger error"})
        
        # Получаем THINKING
        websocket.receive_json()
        
        # Получаем ERROR (шлюз отправляет JSON с ключом error при исключении в httpx)
        resp = websocket.receive_json()
        assert "error" in resp
        assert "Lawyer Assistant Service unavailable" in resp["error"]

def test_websocket_invalid_json(client):
    """Злой тест: Отправка битого JSON в сокет"""
    with client.websocket_connect("/ws/cases/1/chat") as websocket:
        websocket.send_text("not a json")
        resp = websocket.receive_json()
        assert "error" in resp
        assert resp["error"] == "Invalid JSON format"
