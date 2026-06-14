import pytest
import respx
from httpx import Response, ConnectTimeout
from fastapi import status

INTAKE_URL = "http://intake-agent:8001"
LAWYER_URL = "http://lawyer-service:8002"

@respx.mock
def test_list_cases_success(client, respx_mock):
    """Проверка успешного получения списка дел"""
    respx_mock.get(f"{INTAKE_URL}/cases").mock(return_value=Response(200, json=[{"id": 1, "name": "Test Case"}]))
    
    response = client.get("/cases")
    assert response.status_code == 200
    assert response.json() == [{"id": 1, "name": "Test Case"}]

@respx.mock
def test_list_cases_intake_error(client, respx_mock):
    """Злой тест: Intake Service падает (502)"""
    respx_mock.get(f"{INTAKE_URL}/cases").mock(return_value=Response(502))
    
    response = client.get("/cases")
    assert response.status_code == 502
    assert "Intake Service Error" in response.json()["detail"]

@respx.mock
def test_list_cases_timeout(client, respx_mock):
    """Злой тест: Intake Service не отвечает (Timeout)"""
    respx_mock.get(f"{INTAKE_URL}/cases").mock(side_effect=ConnectTimeout)
    
    response = client.get("/cases")
    assert response.status_code == 502
    assert "Service Communication Error" in response.json()["detail"] or "Intake Service Error" in response.json()["detail"]

@respx.mock
def test_get_case_details_success(client, respx_mock):
    """Проверка успешного получения деталей дела (агрегация из двух сервисов)"""
    respx_mock.get(f"{INTAKE_URL}/case/1").mock(return_value=Response(200, json={
        "case": {"id": 1, "case_file": "Docs"},
        "messages": [{"sender_role": "user", "content": "Hello"}]
    }))
    respx_mock.get(f"{LAWYER_URL}/messages/1").mock(return_value=Response(200, json=[
        {"sender_role": "ai_lawyer", "content": "How can I help?"}
    ]))
    
    response = client.get("/cases/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][1]["content"] == "How can I help?"

@respx.mock
def test_get_case_not_found(client, respx_mock):
    """Злой тест: Дела нет в Intake Service"""
    respx_mock.get(f"{INTAKE_URL}/case/999").mock(return_value=Response(404))
    
    response = client.get("/cases/999")
    assert response.status_code == 404
    assert "Case not found" in response.json()["detail"]

@respx.mock
def test_get_case_lawyer_service_fails(client, respx_mock):
    """Злой тест: Lawyer Service падает, но Intake Service ок. 
    Шлюз должен вернуть данные только из Intake."""
    respx_mock.get(f"{INTAKE_URL}/case/1").mock(return_value=Response(200, json={
        "case": {"id": 1, "case_file": "Docs"},
        "messages": [{"sender_role": "user", "content": "Hello"}]
    }))
    respx_mock.get(f"{LAWYER_URL}/messages/1").mock(return_value=Response(500))
    
    response = client.get("/cases/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 1 # Только сообщения от Intake
    assert data["messages"][0]["content"] == "Hello"

@respx.mock
def test_assist_case_success(client, respx_mock):
    """Проверка успешного запроса ассистента"""
    respx_mock.get(f"{INTAKE_URL}/case/1").mock(return_value=Response(200, json={
        "case": {"id": 1, "case_file": "Docs"},
        "messages": [{"sender_role": "user", "content": "Help"}]
    }))
    respx_mock.post(f"{LAWYER_URL}/analyze").mock(return_value=Response(200, json={"response": "Analysis"}))
    
    response = client.post("/cases/1/assist", json={"message": "Analyze this"})
    assert response.status_code == 200
    assert response.json()["response"] == "Analysis"

@respx.mock
def test_assist_case_lawyer_timeout(client, respx_mock):
    """Злой тест: Lawyer Service тормозит (>60с)"""
    respx_mock.get(f"{INTAKE_URL}/case/1").mock(return_value=Response(200, json={
        "case": {"id": 1, "case_file": "Docs"},
        "messages": []
    }))
    # Симулируем таймаут
    respx_mock.post(f"{LAWYER_URL}/analyze").mock(side_effect=ConnectTimeout)
    
    response = client.post("/cases/1/assist", json={"message": "Analyze"})
    assert response.status_code == 502
    assert "Service Communication Error" in response.json()["detail"]

def test_assist_case_invalid_payload(client):
    """Злой тест: Отправка невалидного JSON (Pydantic validation)"""
    response = client.post("/cases/1/assist", json={"wrong_key": "data"})
    assert response.status_code == 422 # Unprocessable Entity
