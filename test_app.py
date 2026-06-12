import requests
import json
import time

def test_workflow():
    base_url = "http://localhost:8000"
    user_id = 1
    
    try:
        # 1. Start chat
        print("--- ШАГ 1: Начало диалога ---")
        res = requests.post(f"{base_url}/chat", json={
            "user_id": user_id,
            "message": "Здравствуйте, у меня проблема. Работодатель не выплачивает зарплату уже два месяца."
        })
        res.raise_for_status()
        data = res.json()
        case_id = data["case_id"]
        print(f"ИИ: {data['response']}")
        
        # 2. Еще одно уточнение (имитация диалога)
        print("\n--- ШАГ 2: Уточнение ---")
        res = requests.post(f"{base_url}/chat", json={
            "user_id": user_id,
            "case_id": case_id,
            "message": "Я работаю официально по трудовому договору в Москве."
        })
        data = res.json()
        print(f"ИИ: {data['response']}")

        # 3. Подтверждение
        print("\n--- ШАГ 3: Подтверждение ---")
        res = requests.post(f"{base_url}/chat", json={
            "user_id": user_id,
            "case_id": case_id,
            "message": "Да, подтверждаю, сформировать заявку."
        })
        data = res.json()
        print(f"ИИ: {data['response']}")
        print(f"Статус дела: {data['status']}")
        
        # 4. Проверка досье
        print("\n--- ШАГ 4: Проверка досье ---")
        time.sleep(2) # Небольшая пауза для завершения фоновых процессов, если они асинхронны (в нашем случае invoke блокирующий)
        res = requests.get(f"{base_url}/cases/{case_id}")
        case_data = res.json()
        print(f"Досье (первые 300 символов):\n{case_data['case']['case_file'][:300]}...")

    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
        print("Убедитесь, что бэкенд запущен (python backend/main.py)")

if __name__ == "__main__":
    test_workflow()
