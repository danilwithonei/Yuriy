from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Глобальные соединения для дашборда (список дел)
        self.dashboard_connections: List[WebSocket] = []
        # Соединения для конкретных чатов дел
        self.case_connections: Dict[int, List[WebSocket]] = {}

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.append(websocket)

    def disconnect_dashboard(self, websocket: WebSocket):
        if websocket in self.dashboard_connections:
            self.dashboard_connections.remove(websocket)

    async def broadcast_dashboard(self, message: dict):
        """Отправка сообщения всем подключенным к дашборду"""
        for connection in self.dashboard_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Если соединение мертво, оно удалится при разрыве, но здесь мы игнорируем ошибки рассылки
                pass

    async def connect_case(self, case_id: int, websocket: WebSocket):
        await websocket.accept()
        if case_id not in self.case_connections:
            self.case_connections[case_id] = []
        self.case_connections[case_id].append(websocket)

    def disconnect_case(self, case_id: int, websocket: WebSocket):
        if case_id in self.case_connections:
            if websocket in self.case_connections[case_id]:
                self.case_connections[case_id].remove(websocket)
            if not self.case_connections[case_id]:
                del self.case_connections[case_id]

    async def send_case_message(self, case_id: int, message: dict):
        """Отправка сообщения всем участникам чата конкретного дела"""
        if case_id in self.case_connections:
            for connection in self.case_connections[case_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()
