import pytest
import respx
from httpx import Response, ConnectTimeout

from conftest import INTAKE_URL

class TestListCases:
    @respx.mock
    def test_list_cases_empty_for_unknown_lawyer(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/cases", params={"lawyer_id": 1}).mock(return_value=Response(200, json=[]))
        resp = client.get("/cases", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @respx.mock
    def test_list_cases_intake_timeout(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/cases", params={"lawyer_id": 1}).mock(side_effect=ConnectTimeout)
        resp = client.get("/cases", headers=auth_headers)
        assert resp.status_code == 502

    @respx.mock
    def test_list_cases_intake_500(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/cases", params={"lawyer_id": 1}).mock(return_value=Response(500))
        resp = client.get("/cases", headers=auth_headers)
        assert resp.status_code == 502

    @respx.mock
    def test_list_cases_intake_garbage_response(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/cases", params={"lawyer_id": 1}).mock(return_value=Response(200, content=b"not json"))
        resp = client.get("/cases", headers=auth_headers)
        assert resp.status_code == 502