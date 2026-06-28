from datetime import UTC

import pytest
import respx
from conftest import INTAKE_URL, LAWYER_URL
from httpx import Response
from starlette.websockets import WebSocketDisconnect

CASE_UUID = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"


class TestWebSocketAuth:
    def test_ws_no_token(self, client):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/cases/{CASE_UUID}/chat"):
                pass
        assert exc.value.code == 4001

    def test_ws_bad_token(self, client):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/cases/{CASE_UUID}/chat?token=garbage"):
                pass
        assert exc.value.code == 4001

    def test_ws_expired_token(self, client):
        from datetime import datetime, timedelta

        from jose import jwt

        from auth import ALGORITHM, SECRET_KEY

        payload = {"sub": "1", "exp": datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/cases/{CASE_UUID}/chat?token={token}"):
                pass
        assert exc.value.code == 4001

    @respx.mock
    def test_ws_foreign_case_forbidden(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/case/{CASE_UUID}").mock(
            return_value=Response(
                200, json={"case": {"id": CASE_UUID, "lawyer_id": 999, "title": None, "summary": None}, "messages": []}
            )
        )
        token = auth_headers["Authorization"].split(" ")[1]
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/cases/{CASE_UUID}/chat?token={token}"):
                pass
        assert exc.value.code == 4003

    @respx.mock
    def test_ws_own_case_works(self, client, auth_headers, respx_mock):
        respx_mock.get(f"{INTAKE_URL}/case/{CASE_UUID}").mock(
            return_value=Response(
                200,
                json={
                    "case": {
                        "id": CASE_UUID,
                        "lawyer_id": 1,
                        "case_file": "Dossier",
                        "case_type": "direct",
                        "title": None,
                        "summary": None,
                    },
                    "messages": [],
                },
            )
        )
        sse_body = b'data: {"token": "OK"}\n\ndata: {"done": true}\n\n'
        respx_mock.post(f"{LAWYER_URL}/analyze").mock(return_value=Response(200, content=sse_body))
        token = auth_headers["Authorization"].split(" ")[1]
        with client.websocket_connect(f"/ws/cases/{CASE_UUID}/chat?token={token}") as ws:
            ws.send_json({"message": "Hi"})
            ws.receive_json()  # AI_THINKING
            while True:
                msg = ws.receive_json()
                if msg["type"] == "AI_RESPONSE":
                    assert msg["content"] == "OK"
                    break
