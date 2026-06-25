import pytest
import respx
from httpx import Response, ConnectTimeout

from conftest import INTAKE_URL, LAWYER_URL

CASE_ID = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"

@respx.mock
def test_list_cases_success(client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/cases", params={"lawyer_id": 1}).mock(return_value=Response(200, json=[{"id": CASE_ID, "name": "Test Case"}]))
    response = client.get("/cases", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == [{"id": CASE_ID, "name": "Test Case"}]

@respx.mock
def test_list_cases_intake_error(client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/cases", params={"lawyer_id": 1}).mock(return_value=Response(502))
    response = client.get("/cases", headers=auth_headers)
    assert response.status_code == 502
    assert "Intake Service Error" in response.json()["detail"]

@respx.mock
def test_list_cases_timeout(client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/cases", params={"lawyer_id": 1}).mock(side_effect=ConnectTimeout)
    response = client.get("/cases", headers=auth_headers)
    assert response.status_code == 502

@respx.mock
def test_get_case_details_success(client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(return_value=Response(200, json={
        "case": {"id": CASE_ID, "client_id": 1, "lawyer_id": 1, "case_file": "Docs", "title": None, "summary": None},
        "messages": [{"sender_role": "user", "content": "Hello"}]
    }))
    respx_mock.get(f"{LAWYER_URL}/messages/{CASE_ID}").mock(return_value=Response(200, json=[
        {"sender_role": "ai_lawyer", "content": "How can I help?"}
    ]))
    response = client.get(f"/cases/{CASE_ID}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][1]["content"] == "How can I help?"

@respx.mock
def test_get_case_not_found(client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(return_value=Response(404))
    response = client.get(f"/cases/{CASE_ID}", headers=auth_headers)
    assert response.status_code == 404
    assert "Case not found" in response.json()["detail"]

@respx.mock
def test_get_case_lawyer_service_fails(client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(return_value=Response(200, json={
        "case": {"id": CASE_ID, "client_id": 1, "lawyer_id": 1, "case_file": "Docs", "title": None, "summary": None},
        "messages": [{"sender_role": "user", "content": "Hello"}]
    }))
    respx_mock.get(f"{LAWYER_URL}/messages/{CASE_ID}").mock(return_value=Response(500))
    response = client.get(f"/cases/{CASE_ID}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "Hello"

@respx.mock
def test_assist_case_success(client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(return_value=Response(200, json={
        "case": {"id": CASE_ID, "client_id": 1, "lawyer_id": 1, "case_file": "Docs", "title": None, "summary": None},
        "messages": [{"sender_role": "user", "content": "Help"}]
    }))
    respx_mock.post(f"{LAWYER_URL}/analyze").mock(return_value=Response(200, content=b"data: {\"token\": \"Analysis\"}\n\ndata: {\"done\": true}\n\n"))
    response = client.post(f"/cases/{CASE_ID}/assist", json={"message": "Analyze this"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["response"] == "Analysis"

@respx.mock
def test_assist_case_lawyer_timeout(client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(return_value=Response(200, json={
        "case": {"id": CASE_ID, "client_id": 1, "lawyer_id": 1, "case_file": "Docs", "title": None, "summary": None},
        "messages": []
    }))
    respx_mock.post(f"{LAWYER_URL}/analyze").mock(side_effect=ConnectTimeout)
    response = client.post(f"/cases/{CASE_ID}/assist", json={"message": "Analyze"}, headers=auth_headers)
    assert response.status_code == 502

def test_assist_case_invalid_payload(client, auth_headers):
    response = client.post(f"/cases/{CASE_ID}/assist", json={"wrong_key": "data"}, headers=auth_headers)
    assert response.status_code == 422