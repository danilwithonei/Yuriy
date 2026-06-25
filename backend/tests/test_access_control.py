import pytest
import respx
from httpx import Response, ConnectTimeout

from conftest import INTAKE_URL, LAWYER_URL

CASE_UUID = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
FOREIGN_UUID = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
MISSING_UUID = "cccccccc-cccc-4ccc-cccc-cccccccccccc"

def _mock_case(respx_mock, case_id: str, lawyer_id: int):
    respx_mock.get(f"{INTAKE_URL}/case/{case_id}").mock(return_value=Response(200, json={
        "case": {"id": case_id, "client_id": 1, "lawyer_id": lawyer_id, "status": "open", "case_type": "direct", "title": None, "summary": None},
        "messages": []
    }))

def _mock_case_no_lawyer(respx_mock, case_id: str):
    respx_mock.get(f"{INTAKE_URL}/case/{case_id}").mock(return_value=Response(200, json={
        "case": {"id": case_id, "client_id": 1, "lawyer_id": None, "status": "open", "case_type": "direct", "title": None, "summary": None},
        "messages": []
    }))

class TestOwnershipGet:
    @respx.mock
    def test_get_own_case_ok(self, client, auth_headers, respx_mock):
        _mock_case(respx_mock, CASE_UUID, 1)
        resp = client.get(f"/cases/{CASE_UUID}", headers=auth_headers)
        assert resp.status_code == 200

    @respx.mock
    def test_get_foreign_case_forbidden(self, client, auth_headers, respx_mock):
        _mock_case(respx_mock, CASE_UUID, 999)
        resp = client.get(f"/cases/{CASE_UUID}", headers=auth_headers)
        assert resp.status_code == 403

    @respx.mock
    def test_get_case_no_lawyer_allowed(self, client, auth_headers, respx_mock):
        _mock_case_no_lawyer(respx_mock, CASE_UUID)
        resp = client.get(f"/cases/{CASE_UUID}", headers=auth_headers)
        assert resp.status_code == 200

    @respx.mock
    def test_get_case_not_found(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/case/{MISSING_UUID}").mock(return_value=Response(404))
        resp = client.get(f"/cases/{MISSING_UUID}", headers=auth_headers)
        assert resp.status_code == 404

    @respx.mock
    def test_get_case_intake_down(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/case/{CASE_UUID}").mock(side_effect=ConnectTimeout)
        resp = client.get(f"/cases/{CASE_UUID}", headers=auth_headers)
        assert resp.status_code == 502

class TestOwnershipPost:
    @respx.mock
    def test_assist_foreign_case_forbidden(self, client, auth_headers, respx_mock):
        _mock_case(respx_mock, CASE_UUID, 999)
        resp = client.post(f"/cases/{CASE_UUID}/assist", json={"message": "Hello"}, headers=auth_headers)
        assert resp.status_code == 403

    @respx.mock
    def test_assist_case_not_found(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/case/{CASE_UUID}").mock(return_value=Response(404))
        resp = client.post(f"/cases/{CASE_UUID}/assist", json={"message": "Hello"}, headers=auth_headers)
        assert resp.status_code == 404

    @respx.mock
    def test_assist_case_intake_down(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/case/{CASE_UUID}").mock(side_effect=ConnectTimeout)
        resp = client.post(f"/cases/{CASE_UUID}/assist", json={"message": "Hello"}, headers=auth_headers)
        assert resp.status_code == 502

    @respx.mock
    def test_assist_foreign_case_detail(self, client, auth_headers, respx_mock):
        _mock_case(respx_mock, CASE_UUID, 999)
        resp = client.post(f"/cases/{CASE_UUID}/assist", json={"message": "Hello"}, headers=auth_headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Access denied"

    @respx.mock
    def test_intake_chat_foreign_case_forbidden(self, client, auth_headers, respx_mock):
        _mock_case(respx_mock, CASE_UUID, 999)
        resp = client.post(f"/cases/{CASE_UUID}/intake/chat", json={"message": "Hello"}, headers=auth_headers)
        assert resp.status_code == 403

    @respx.mock
    def test_intake_confirm_foreign_case_forbidden(self, client, auth_headers, respx_mock):
        _mock_case(respx_mock, CASE_UUID, 999)
        resp = client.post(f"/cases/{CASE_UUID}/intake/confirm", json={}, headers=auth_headers)
        assert resp.status_code == 403