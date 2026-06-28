import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

INTAKE_SERVICE_URL = os.getenv("INTAKE_SERVICE_URL", "http://intake-agent:8001")
LAWYER_SERVICE_URL = os.getenv("LAWYER_SERVICE_URL", "http://lawyer-service:8002")

TIMEOUT_DEFAULT = 30.0
TIMEOUT_STREAM = 120.0


class ServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class IntakeClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or INTAKE_SERVICE_URL

    @asynccontextmanager
    async def _request(
        self, method: str, path: str, timeout: float = TIMEOUT_DEFAULT, **kwargs
    ) -> AsyncIterator[httpx.Response]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                res = await client.request(method, url, **kwargs)
                yield res
            except httpx.RequestError as e:
                raise httpx.RequestError(f"Intake Service unavailable: {e}") from e

    @asynccontextmanager
    async def _stream(
        self, method: str, path: str, timeout: float = TIMEOUT_STREAM, **kwargs
    ) -> AsyncIterator[httpx.Response]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream(method, url, **kwargs) as res:
                    yield res
            except httpx.RequestError as e:
                raise httpx.RequestError(f"Intake Service unavailable: {e}") from e

    async def _check_response(self, res: httpx.Response):
        if res.status_code != 200:
            detail = "Service error"
            try:
                body = res.json()
                detail = body.get("detail", detail)
            except Exception:
                pass
            raise ServiceError(res.status_code, detail)

    async def get_case(self, case_id: str) -> dict:
        async with self._request("GET", f"/case/{case_id}") as res:
            await self._check_response(res)
            return res.json()

    async def list_cases(self, lawyer_id: int) -> list:
        async with self._request("GET", "/cases", params={"lawyer_id": lawyer_id}) as res:
            await self._check_response(res)
            return res.json()

    async def create_case(self, case_type: str, source: str, lawyer_id: int) -> dict:
        async with self._request(
            "POST", "/create-case", json={"case_type": case_type, "source": source, "lawyer_id": lawyer_id}
        ) as res:
            await self._check_response(res)
            return res.json()

    async def chat_stream(self, case_id: str, message: str) -> AsyncIterator[dict]:
        async with self._stream(
            "POST",
            "/chat",
            json={
                "external_id": "lawyer_default",
                "source": "frontend",
                "case_id": case_id,
                "message": message,
            },
        ) as res:
            from yuriy_shared.sse import parse_sse_line

            if res.status_code != 200:
                try:
                    body = await res.aread()
                    error_detail = body.json().get("detail", "Intake Service error")
                except Exception:
                    error_detail = "Intake Service error"
                yield {"error": error_detail}
                return

            content_type = res.headers.get("content-type", "")
            is_sse = "text/event-stream" in content_type

            if not is_sse:
                body = await res.aread()
                data = body.json()
                yield data
                yield {"done": True}
                return

            async for line in res.aiter_lines():
                data = parse_sse_line(line)
                if data is None:
                    continue
                yield data
                if data.get("done") or "error" in data:
                    return

    async def confirm(self, case_id: str) -> dict:
        async with self._request("POST", "/confirm", json={"case_id": case_id}) as res:
            await self._check_response(res)
            return res.json()

    async def pin(self, case_id: str, pinned: bool) -> dict:
        async with self._request("PATCH", f"/case/{case_id}/pin", json={"pinned": pinned}) as res:
            await self._check_response(res)
            return res.json()

    async def delete(self, case_id: str) -> dict:
        async with self._request("DELETE", f"/case/{case_id}") as res:
            await self._check_response(res)
            return res.json()


class LawyerClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or LAWYER_SERVICE_URL

    @asynccontextmanager
    async def _request(
        self, method: str, path: str, timeout: float = TIMEOUT_DEFAULT, **kwargs
    ) -> AsyncIterator[httpx.Response]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                res = await client.request(method, url, **kwargs)
                yield res
            except httpx.RequestError as e:
                raise httpx.RequestError(f"Lawyer Service unavailable: {e}") from e

    @asynccontextmanager
    async def _stream(
        self, method: str, path: str, timeout: float = TIMEOUT_STREAM, **kwargs
    ) -> AsyncIterator[httpx.Response]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream(method, url, **kwargs) as res:
                    yield res
            except httpx.RequestError as e:
                raise httpx.RequestError(f"Lawyer Service unavailable: {e}") from e

    async def get_messages(self, case_id: str) -> list:
        async with self._request("GET", f"/messages/{case_id}") as res:
            if res.status_code == 200:
                return res.json()
            return []

    async def analyze_stream(
        self, case_id: str, case_file: str, history: str, query: str, search_web: bool = False
    ) -> AsyncIterator[dict]:
        async with self._stream(
            "POST",
            "/analyze",
            json={
                "case_id": case_id,
                "case_file": case_file,
                "history": history,
                "query": query,
                "search_web": search_web,
            },
        ) as res:
            from yuriy_shared.sse import parse_sse_line

            if res.status_code != 200:
                try:
                    body = await res.aread()
                    error_detail = body.json().get("detail", "Lawyer Assistant Service error")
                except Exception:
                    error_detail = "Lawyer Assistant Service error"
                yield {"error": error_detail}
                return

            async for line in res.aiter_lines():
                data = parse_sse_line(line)
                if data is None:
                    continue
                yield data

    async def pin(self, case_id: str, pinned: bool) -> dict | None:
        async with self._request("PATCH", f"/case/{case_id}/pin", json={"pinned": pinned}) as res:
            if res.status_code == 200:
                return res.json()
            return None

    async def delete(self, case_id: str) -> dict | None:
        async with self._request("DELETE", f"/case/{case_id}") as res:
            if res.status_code == 200:
                return res.json()
            return None
