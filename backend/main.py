from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ws_manager import manager
from core.logger import logger
import os
import uvicorn
import httpx

app = FastAPI(title="Yuriy Lawyer Dashboard Gateway")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INTAKE_SERVICE_URL = os.getenv("INTAKE_SERVICE_URL", "http://intake-agent:8001")
LAWYER_SERVICE_URL = os.getenv("LAWYER_SERVICE_URL", "http://lawyer-service:8002")

@app.get("/")
def read_root():
    logger.info("Health check endpoint called")
    return {"message": "Lawyer Dashboard Gateway is running"}

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect_dashboard(websocket)
    logger.info("Dashboard WebSocket connected")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
        logger.info("Dashboard WebSocket disconnected")

@app.websocket("/ws/cases/{case_id}/chat")
async def websocket_case_chat(websocket: WebSocket, case_id: int):
    await manager.connect_case(case_id, websocket)
    logger.info(f"Case chat WebSocket connected for case_id={case_id}")
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.warning(f"Invalid JSON received on WebSocket case_id={case_id}: {e}")
                try:
                    await websocket.send_json({"error": "Invalid JSON format"})
                except Exception:
                    pass
                continue
                
            message_text = data.get("message")
            if message_text:
                logger.info(f"Received WS message for case_id={case_id}: {message_text[:50]}...")
                async with httpx.AsyncClient() as client:
                    # 1. Получаем данные дела из Intake Service
                    try:
                        case_res = await client.get(f"{INTAKE_SERVICE_URL}/case/{case_id}")
                        if case_res.status_code != 200:
                            logger.error(f"Case {case_id} not found in Intake Service")
                            await websocket.send_json({"error": "Case not found in Intake Service"})
                            continue
                    except Exception as e:
                        logger.error(f"Failed to reach Intake Service: {e}")
                        await websocket.send_json({"error": "Intake Service unavailable"})
                        continue
                    
                    case_data = case_res.json()
                    case_file = case_data["case"].get("case_file") or "Досье еще не сформировано."
                    
                    # История клиент-агент
                    intake_history = "\n".join([f"{m['sender_role']}: {m['content']}" for m in case_data["messages"]])
                    
                    await manager.send_case_message(case_id, {"type": "AI_THINKING", "sender": "ai_case"})

                    # 2. Вызываем Lawyer Assistant Service
                    logger.info(f"Calling Lawyer Assistant for case_id={case_id}")
                    try:
                        assist_res = await client.post(f"{LAWYER_SERVICE_URL}/analyze", json={
                            "case_id": case_id,
                            "case_file": case_file,
                            "history": intake_history,
                            "query": message_text
                        }, timeout=60.0)
                        
                        ai_content = assist_res.json()["response"]
                        logger.info(f"AI response received for case_id={case_id}")
                        
                        await manager.send_case_message(case_id, {
                            "type": "AI_RESPONSE",
                            "content": ai_content,
                            "sender": "ai_case"
                        })
                    except Exception as e:
                        logger.error(f"Failed to reach Lawyer Assistant Service: {e}")
                        await websocket.send_json({"error": "Lawyer Assistant Service unavailable"})

    except WebSocketDisconnect:
        manager.disconnect_case(case_id, websocket)
        logger.info(f"Case chat WebSocket disconnected for case_id={case_id}")

@app.get("/cases")
async def list_cases():
    logger.info("Listing all cases")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{INTAKE_SERVICE_URL}/cases")
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching cases from Intake Service: {e}")
            raise HTTPException(status_code=502, detail=f"Intake Service Error: {str(e)}")

@app.get("/cases/{case_id}")
async def get_case(case_id: int):
    logger.info(f"Fetching details for case_id={case_id}")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Запрос к Intake Service
            intake_res = await client.get(f"{INTAKE_SERVICE_URL}/case/{case_id}")
            if intake_res.status_code != 200:
                logger.warning(f"Case {case_id} not found in Intake Service")
                raise HTTPException(status_code=intake_res.status_code, detail="Case not found in Intake Service")
            
            intake_data = intake_res.json()

            # 2. Запрос к Lawyer Service для получения диалогов Юрист-ИИ
            try:
                lawyer_res = await client.get(f"{LAWYER_SERVICE_URL}/messages/{case_id}")
                lawyer_messages = lawyer_res.json() if lawyer_res.status_code == 200 else []
            except Exception as e:
                logger.warning(f"Could not fetch lawyer messages for case {case_id}: {e}")
                lawyer_messages = []

            # 3. Объединяем сообщения
            all_messages = intake_data["messages"] + lawyer_messages
            
            return {
                "case": intake_data["case"],
                "messages": all_messages
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error communicating with backend services for case {case_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Service Communication Error: {str(e)}")

class AssistRequest(BaseModel):
    message: str

@app.post("/cases/{case_id}/assist")
async def assist_case(case_id: int, request: AssistRequest):
    logger.info(f"Manual assist request for case_id={case_id}")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Получаем данные дела
            case_res = await client.get(f"{INTAKE_SERVICE_URL}/case/{case_id}")
            case_data = case_res.json()
            
            # 2. Анализируем
            logger.info(f"Analyzing case {case_id} for manual assist")
            assist_res = await client.post(f"{LAWYER_SERVICE_URL}/analyze", json={
                "case_id": case_id,
                "case_file": case_data["case"].get("case_file") or "Досье еще не сформировано.",
                "history": "\n".join([f"{m['sender_role']}: {m['content']}" for m in case_data["messages"]]),
                "query": request.message
            }, timeout=60.0)
            
            return assist_res.json()
        except Exception as e:
            logger.error(f"Error in manual assist for case {case_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Service Communication Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
