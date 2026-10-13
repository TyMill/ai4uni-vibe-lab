# AI4UNI Vibe Coding Lab

Public, **no-login** workshop: JupyterLite/Pyodide notebook on GitHub Pages and a separate FastAPI proxy to OpenAI Responses API. Participants write prompts in the left panel, **review and copy generated code**, then paste/run it in the right-hand notebook. **Code transfer is manual by design**, not automatic execution. No OpenAI key is ever sent to the browser.

## Architecture

`Browser → GitHub Pages (static prompt UI + JupyterLite)`

`Browser prompt → HTTPS FastAPI backend (Render) → OpenAI Responses API → code displayed in browser`

`Generated code → user reviews + copies → Pyodide executes in user's browser`

## Deploy in ~15 minutes

1. Create a **public GitHub repository** containing these files (e.g. `ai4uni-vibe-lab`). Set repository default branch to `main`.
2. At [Render](https://dashboard.render.com/), create a Blueprint from that repository (`render.yaml`) or a Python web service with root directory `backend`; build `pip install -r requirements.txt`; start `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`.
3. Configure **Render environment secrets**: `OPENAI_API_KEY` (never commit it), `ALLOWED_ORIGIN=https://YOUR_USERNAME.github.io` (for normal GitHub Pages URLs **origin only**, no `/repo`). Optional `OPENAI_MODEL=gpt-5-mini`. Ensure the API account has project funding and model access.
4. Copy your Render HTTPS URL to `frontend/config.js`, e.g. `https://ai4uni-workshop-api.onrender.com`. Commit and push.
5. In GitHub repository **Settings → Pages**, select **GitHub Actions** as deployment source; workflow `.github/workflows/pages.yml` builds JupyterLite.
6. Wait for the green workflow. Your participant link will be `https://YOUR_USERNAME.github.io/ai4uni-vibe-lab/` (the exact repo name matters). Share **only** this URL with participants.
7. Smoke-test in a **private/incognito window**, not logged in: open the link; run starter cell; generate code; copy/paste into notebook; run Shift+Enter.

**Note:** On organization GitHub Pages domains, the origin is `https://ORG.github.io`. If using a custom Pages domain, update `ALLOWED_ORIGIN` accordingly.

## Local development

Terminal A:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY='your-secret-api-key'
export ALLOWED_ORIGIN='http://localhost:8000'
uvicorn main:app --host 127.0.0.1 --port 8001
```

Terminal B (repo root):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-jupyterlite.txt
jupyter lite build --contents content --output-dir dist/jupyter
cp frontend/index.html frontend/config.js dist/
# change dist/config.js to http://localhost:8001 for local development
python -m http.server 8000 -d dist
```

## Workshop controls and limitations

- This public API has **no user authentication**. CORS + Origin checking protects browsers' ordinary cross-origin usage but **is not real authentication**; clients can forge Origin headers.
- In-memory global quotas are **best effort**, reset when the backend restarts, and are **not safe across multiple workers/replicas**. Use exactly **one worker/instance** for this demo.
- Set a strict usage budget / alert within your **OpenAI API project**, monitor usage, and shut down the proxy after the workshop. For stronger financial guarantees, put a persistent atomic quota in Redis/managed storage, enforce spending at the infrastructure/gateway layer, and consider request attestation or per-participant short-lived passes.
- Output tokens are capped, but actual spend also depends on input tokens and model pricing. No client-facing rate limit is a hard monetary spending cap.
- Prompts go to the OpenAI API. **Do not enter personal, confidential, or unpublished research data**; use synthetic datasets only.
- Pyodide executes code in the browser, not on the proxy server, but generated code remains untrusted and browser-side code may use network APIs. Avoid secrets in the workshop browser session and review all generated code.
- Model output can violate instructions or use incompatible libraries. Users must review and may need to revise the prompt.
- JupyterLite stores working files in browser storage, subject to browser constraints. Participants can export `.ipynb` files to keep them.
- Pyodide startup and package loading may take time; allow at least 30–60 seconds on first load.
- `GET /health` checks whether the backend is up. To disable generation, set `WORKSHOP_ENABLED=false` in backend environment and redeploy/restart. To stop all spend, remove/disable the API key or suspend the hosting service.

## Before inviting participants

- [ ] OpenAI key only in Render secret env variables
- [ ] Correct frontend `config.js` and backend `ALLOWED_ORIGIN`
- [ ] GitHub Pages action is green; JupyterLite loads and Python starter runs
- [ ] Test a real model request end-to-end in incognito mode
- [ ] Check spend controls, usage monitoring, model access, participants' network/firewall access
- [ ] Arrange a fallback: plain JupyterLite tasks if backend unavailable
- [ ] Confirm accessibility and browser compatibility on real participant devices

Official references: https://jupyterlite.readthedocs.io/en/stable/quickstart/standalone.html ; https://github.com/jupyterlite/jupyterlite/blob/main/docs/quickstart/deploy.md ; https://render.com/docs/deploy-fastapi ; https://platform.openai.com/docs/api-reference/responses
