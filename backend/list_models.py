import requests
import os
from dotenv import load_dotenv

load_dotenv()

def list_available_models():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    # Используем ваш специфический эндпоинт
    base_url = "https://ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        print(f"Запрос списка моделей к {base_url}/models...")
        response = requests.get(f"{base_url}/models", headers=headers)
        response.raise_for_status()
        
        models_data = response.json()
        print("\nДоступные модели:")
        for model in models_data.get("data", []):
            print(f"- {model['id']}")
            
        if not models_data.get("data"):
            print("Список моделей пуст. Возможно, эндпоинт не поддерживает метод GET /models или у вас нет прав.")
            
    except Exception as e:
        print(f"\nОшибка при получении списка моделей: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Ответ сервера: {e.response.text}")

if __name__ == "__main__":
    list_available_models()
