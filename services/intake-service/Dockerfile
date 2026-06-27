FROM python:3.11-slim

WORKDIR /app

COPY packages/shared /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

COPY services/intake-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/intake-service/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
