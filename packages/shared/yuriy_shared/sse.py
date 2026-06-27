import json
from typing import Any


def parse_sse_line(line: str) -> dict[str, Any] | None:
    if not line.startswith("data: "):
        return None
    payload = line[6:]
    if not payload.strip():
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None
