FROM python:3.11-slim

WORKDIR /app

COPY packages/shared /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

COPY services/bot-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/bot-service/ .

CMD ["python", "main.py"]
