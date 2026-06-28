from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from auth import get_lawyer_or_none
from core.logger import logger
from routers.deps import lawyer, verify_ownership
from ws_manager import manager

router = APIRouter()


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    lawyer_id = get_lawyer_or_none(token)
    if lawyer_id is None:
        await websocket.close(code=4001)
        return
    await manager.connect_dashboard(websocket)
    logger.info(f"Dashboard WebSocket connected for lawyer_id={lawyer_id}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
        logger.info(f"Dashboard WebSocket disconnected for lawyer_id={lawyer_id}")


@router.websocket("/ws/cases/{case_id}/chat")
async def websocket_case_chat(websocket: WebSocket, case_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    lawyer_id = get_lawyer_or_none(token)
    if lawyer_id is None:
        await websocket.close(code=4001)
        return
    try:
        case_data = await verify_ownership(case_id, lawyer_id)
    except HTTPException as e:
        code = {404: 4004, 403: 4003}.get(e.status_code, 4002)
        await websocket.close(code=code)
        return
    await manager.connect_case(case_id, websocket)
    logger.info(f"Case chat WebSocket connected for case_id={case_id}, lawyer_id={lawyer_id}")
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.warning(f"Invalid JSON received on WebSocket case_id={case_id}: {e}")
                try:
                    await websocket.send_json({"type": "AI_ERROR", "error": "Invalid JSON format"})
                except Exception:
                    pass
                continue

            message_text = data.get("message")
            if not message_text:
                continue

            logger.info(f"Received WS message for case_id={case_id}: {message_text[:50]}...")
            case_type = case_data["case"].get("case_type", "intake")
            is_direct = case_type == "direct"
            if is_direct:
                case_file = ""
                intake_history = ""
            else:
                case_file = case_data["case"].get("case_file") or "Досье еще не сформировано."
                intake_history = "\n".join([f"{m['sender_role']}: {m['content']}" for m in case_data["messages"]])

            await manager.send_case_message(case_id, {"type": "AI_THINKING", "sender": "ai_case"})

            logger.info(f"Streaming from Lawyer Assistant for case_id={case_id}")
            try:
                full_content = ""
                async for sse_data in lawyer.analyze_stream(
                    case_id, case_file, intake_history, message_text, search_web=is_direct
                ):
                    if "token" in sse_data:
                        full_content += sse_data["token"]
                        await manager.send_case_message(
                            case_id,
                            {
                                "type": "AI_TOKEN",
                                "token": sse_data["token"],
                            },
                        )
                    elif "error" in sse_data:
                        logger.error(f"SSE error for case_id={case_id}: {sse_data['error']}")
                        await manager.send_case_message(case_id, {"type": "AI_ERROR", "error": sse_data["error"]})
                        break
                    elif sse_data.get("done"):
                        logger.info(f"SSE done for case_id={case_id}: {len(full_content)} chars")
                        await manager.send_case_message(
                            case_id,
                            {
                                "type": "AI_RESPONSE",
                                "content": full_content,
                                "sender": "ai_case",
                            },
                        )
            except Exception as e:
                logger.error(f"Failed to reach Lawyer Assistant Service: {e}")
                await manager.send_case_message(
                    case_id, {"type": "AI_ERROR", "error": "Lawyer Assistant Service unavailable"}
                )

    except WebSocketDisconnect:
        manager.disconnect_case(case_id, websocket)
        logger.info(f"Case chat WebSocket disconnected for case_id={case_id}")
