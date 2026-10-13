"""Public workshop proxy. No user-supplied code is executed on this server."""
import asyncio
import os
import time
from collections import deque
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
MODEL = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
ALLOWED_ORIGIN = os.getenv('ALLOWED_ORIGIN', 'http://localhost:8000').rstrip('/')
MAX_REQUESTS_TOTAL = int(os.getenv('MAX_REQUESTS_TOTAL', '300'))
MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '12'))
MAX_OUTPUT_TOKENS = min(int(os.getenv('MAX_OUTPUT_TOKENS', '900')), 1500)
WORKSHOP_ENABLED = os.getenv('WORKSHOP_ENABLED', 'true').lower() == 'true'

app = FastAPI(title='AI4UNI Workshop Proxy', docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=[ALLOWED_ORIGIN], allow_methods=['POST', 'GET'], allow_headers=['Content-Type'])
lock = asyncio.Lock()
started_at = datetime.now(timezone.utc).isoformat()
recent = deque()
calls = 0

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=1800)

@app.get('/health')
async def health():
    return {'status':'ok' if WORKSHOP_ENABLED else 'disabled', 'model': MODEL, 'started_at': started_at}

@app.post('/api/generate')
async def generate(data: GenerateRequest, request: Request):
    global calls
    if not WORKSHOP_ENABLED:
        raise HTTPException(503, 'The workshop is currently closed.')
    if not OPENAI_API_KEY:
        raise HTTPException(503, 'AI provider is not configured.')
    origin = request.headers.get('origin')
    if origin != ALLOWED_ORIGIN:
        raise HTTPException(403, 'This endpoint accepts requests only from the workshop website.')
    async with lock:
        now = time.monotonic()
        while recent and now - recent[0] > 60:
            recent.popleft()
        if calls >= MAX_REQUESTS_TOTAL:
            raise HTTPException(429, 'Workshop request budget exhausted.')
        if len(recent) >= MAX_REQUESTS_PER_MINUTE:
            raise HTTPException(429, 'Too many requests. Wait one minute.')
        calls += 1  # Count attempts, including failed provider calls.
        recent.append(now)
    instructions = (
        'You are a Python instructor for the AI4UNI university workshop. '
        'Return ONLY a runnable Python code snippet, with short Python comments. '
        'The program runs in browser-based JupyterLite/Pyodide. '
        'Prefer standard Python, numpy, pandas, matplotlib. Avoid pip installs, filesystem secrets, '
        'network access, shell commands, subprocess, eval, exec, os.system and external APIs. '
        'Do not claim synthetic data support causal inference. Keep code concise, under 90 lines. '
        'Do not return markdown fences.'
    )
    body = {
        'model': MODEL,
        'instructions': instructions,
        'input': data.prompt,
        'max_output_tokens': MAX_OUTPUT_TOKENS,
        'store': False,
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post('https://api.openai.com/v1/responses', json=body, headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'})
        if response.status_code != 200:
            raise HTTPException(502, 'The AI provider could not complete the request. Please try again.')
        payload = response.json()
        text = ''.join(part.get('text', '') for item in payload.get('output', [])
                       for part in item.get('content', []) if part.get('type') == 'output_text')
        if not text.strip():
            raise HTTPException(502, 'The model returned no code. Please retry with a simpler prompt.')
        return {'code': text.strip(), 'model': MODEL}
    except httpx.RequestError:
        raise HTTPException(502, 'AI provider connection problem. Please retry.') from None
