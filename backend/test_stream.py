import os
import sys
import time
import json
from dotenv import load_dotenv

# Перенаправляем stdout в utf-8, чтобы избежать проблем с кодировкой в Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

base_host = os.getenv("DASHSCOPE_BASE_HOST", "ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com")
api_key = os.getenv("DASHSCOPE_API_KEY")
model = os.getenv("LLM_MODEL", "qwen3.6-flash")

if not api_key:
    print("[ERROR] DASHSCOPE_API_KEY not set in .env")
    sys.exit(1)

from openai import OpenAI

client = OpenAI(
    api_key=api_key,
    base_url=f"https://{base_host}/compatible-mode/v1",
)

prompt = "Напиши краткое эссе на 3 абзаца о влиянии искусственного интеллекта на юридическую практику. На русском языке."

print(f"Model: {model}")
print(f"Base:  https://{base_host}/compatible-mode/v1")
print(f"Prompt: {prompt[:60]}...")
print("-" * 60)

start = time.monotonic()
token_count = 0
full_text = ""

try:
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        timeout=120,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            token = delta.content
            token_count += 1
            full_text += token
            print(token, end="", flush=True)
            time.sleep(0.02)

except Exception as e:
    print(f"\n[ERROR] {e}")
    sys.exit(1)

elapsed = time.monotonic() - start
tps = token_count / elapsed if elapsed > 0 else 0

print()
print("-" * 60)
print(f"[OK] {token_count} tokens in {elapsed:.2f}s ({tps:.1f} tok/s)")
print(f"     Total chars: {len(full_text)}")
