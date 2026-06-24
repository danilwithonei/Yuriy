from typing import List, Dict
from fastapi import WebSocket
from core.logger import logger

class ConnectionManager:
    def __init__(self):
        # Глобальные соединения для дашборда (список дел)
        self.dashboard_connections: List[WebSocket] = []
        # Соединения для конкретных чатов дел
        self.case_connections: Dict[str, List[WebSocket]] = {}

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.append(websocket)

    def disconnect_dashboard(self, websocket: WebSocket):
        if websocket in self.dashboard_connections:
            self.dashboard_connections.remove(websocket)
            logger.info("Dashboard WebSocket disconnected and cleaned up")

    async def broadcast_dashboard(self, message: dict):
        """Отправка сообщения всем подключенным к дашборду"""
        for connection in self.dashboard_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Dashboard broadcast failed: {e}")

    async def connect_case(self, case_id: str, websocket: WebSocket):
        await websocket.accept()
        if case_id not in self.case_connections:
            self.case_connections[case_id] = []
        self.case_connections[case_id].append(websocket)

    def disconnect_case(self, case_id: str, websocket: WebSocket):
        if case_id in self.case_connections:
            if websocket in self.case_connections[case_id]:
                self.case_connections[case_id].remove(websocket)
                logger.info(f"Case WebSocket disconnected and cleaned up for case_id={case_id}")
            if not self.case_connections[case_id]:
                del self.case_connections[case_id]

    async def send_case_message(self, case_id: str, message: dict):
        """Отправка сообщения всем участникам чата конкретного дела"""
        if case_id in self.case_connections:
            for connection in self.case_connections[case_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Send case message failed for case_id={case_id}: {e}")

manager = ConnectionManager()
