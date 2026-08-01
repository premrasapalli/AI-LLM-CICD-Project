# AI-LLM-CICD-Project — Implementation from Scratch

A beginner-friendly, step-by-step guide showing how this project was built from an empty folder to a complete AI-powered CI/CD system.

---

## Table of contents

1. [What are we building?](#1-what-are-we-building)
2. [Tools you need](#2-tools-you-need)
3. [Step 0 — Start the project](#step-0--start-the-project)
4. [Step 1 — Backend: your first FastAPI app](#step-1--backend-your-first-fastapi-app)
5. [Step 2 — Make the backend read real data](#step-2--make-the-backend-read-real-data)
6. [Step 3 — Store data with SQLite](#step-3--store-data-with-sqlite)
7. [Step 4 — The AI reviewer](#step-4--the-ai-reviewer)
8. [Step 5 — Automate everything with GitHub Actions](#step-5--automate-everything-with-github-actions)
9. [Step 6 — The frontend dashboard](#step-6--the-frontend-dashboard)
10. [Step 7 — Docker](#step-7--docker)
11. [Step 8 — Tests and quality gates](#step-8--tests-and-quality-gates)
12. [Step 9 — Deploy](#step-9--deploy)
13. [The big picture](#the-big-picture)

---

## 1. What are we building?

Three parts that talk to each other:

```
┌──────────────┐    ┌───────────────┐    ┌──────────────────┐
│   Frontend   │───▶│    Backend    │───▶│   GitHub API     │
│  (dashboard) │    │   (FastAPI)   │    │ (real repo data) │
└──────────────┘    │    + SQLite   │    └──────────────────┘
                    └──────┬────────┘
                           │ saves AI reports
                    ┌──────▼────────┐
                    │ GitHub Actions│  runs: lint → test →
                    │  CI pipeline  │  AI review (Ollama) → Docker
                    └───────────────┘
```

- **Backend** — a Python web server that answers questions like "what is the repo's latest CI status?" and stores AI review reports.
- **AI reviewer** — a Python script that reads the project's own code, scores it 0–100, and asks a local AI model (Ollama) for written feedback.
- **CI/CD pipeline** — GitHub automatically runs checks on every push: linting, tests, the AI review, and a Docker build.
- **Dashboard** — a webpage (HTML/CSS/JS) that displays all of this in a nice dark-orange UI.

> **Concept: what is an API?**
> An API is a restaurant menu. The menu (URL) lists dishes (endpoints). You order a dish (make a request), and the kitchen (server) brings you food (a response, usually JSON).

---

## 2. Tools you need

| Tool | Why | Install |
| --- | --- | --- |
| Python 3.10+ | Backend + AI review | `brew install python` |
| Git | Version control | `brew install git` |
| GitHub account | Host the repo + run CI | sign up at github.com |
| Ollama (optional locally) | Run the AI model | `curl -fsSL https://ollama.com/install.sh \| sh` |
| VS Code (any editor) | Write code | code.visualstudio.com |

You do **not** need Node.js — the frontend is plain HTML/CSS/JS.

---

## Step 0 — Start the project

```bash
mkdir AI-LLM-CICD-Project
cd AI-LLM-CICD-Project
git init
git branch -M main
```

Create a `.gitignore` so we never commit junk:

```gitignore
.venv/
__pycache__/
*.pyc
data/
.pytest_cache/
.coverage
```

Create a README and make the first commit:

```bash
git add -A
git commit -m "Initial commit"
```

> **Concept: version control.**
> Git takes "photos" (commits) of your folder. If you break something later, you can go back to any photo. `git init` creates the photo album; `git commit` takes a photo.

---

## Step 1 — Backend: your first FastAPI app

**FastAPI** is a Python framework for building APIs. It's beginner-friendly because a route is just a function.

### 1a. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn
```

> **Concept: virtual environment.**
> A `.venv` is a private folder of Python packages for *this* project, so different projects don't clash. `source .venv/bin/activate` turns it on.

### 1b. Hello world

`backend/main.py`:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "AI LLM CI/CD Backend Running 🚀"}
```

Run it:

```bash
uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000` — you see JSON! That's your first API.

> **Concept: `@app.get("/")`**
> "When someone visits `/`, run this function and send the result back." The decorator `@` is just Python's way of registering the function with the app.

### 1c. Add CORS so the browser can talk to it

A webpage served from `localhost:8080` is *not allowed* to call `localhost:8000` by default (browser security). **CORS** is the permission slip. Add it:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow any website
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **Beginner trap we hit:** `allow_credentials=True` + `"*"` silently breaks CORS. We removed `allow_credentials` because this API needs no cookies. Lesson: read the browser console — "Access-Control-Allow-Origin" errors are almost always CORS config.

---

## Step 2 — Make the backend read real data

A hardcoded `/status` is boring. Let's fetch **real** data from GitHub's public API.

### 2a. The GitHub client

`backend/github_client.py` — a small helper that asks GitHub questions:

```python
import json
import os
import urllib.request

API = "https://api.github.com"
OWNER = os.environ.get("GH_OWNER", "premrasapalli")
REPO  = os.environ.get("GH_REPO", "AI-LLM-CICD-Project")

def _get(path):
    url = f"{API}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

def get_repo():            # repo info (name, stars, language...)
    return _get(f"/repos/{OWNER}/{REPO}")

def get_workflow_runs():   # latest CI runs
    return _get(f"/repos/{OWNER}/{REPO}/actions/runs?per_page=10")
```

> **Concept: endpoints of other people's APIs.**
> GitHub's API has URLs too: `https://api.github.com/repos/premrasapalli/AI-LLM-CICD-Project` returns the repo as JSON. We're just calling those URLs from Python with `urllib`.

### 2b. Wire it into `/status`

In `backend/main.py`, the `/status` endpoint now calls GitHub, reshapes the data into something simple, and caches it:

```python
CACHE_TTL = 60
_cache = {}

def cached(key, fn, ttl=CACHE_TTL):
    now = time.time()
    entry = _cache.get(key)
    if entry and now - entry[0] < ttl:
        return entry[1]
    try:
        value = fn()
        _cache[key] = (now, value)
        return value
    except Exception:
        return entry[1] if entry else None   # fall back to last good value
```

> **Concept: caching.**
> Calling GitHub on every page load is slow and gets you rate-limited. Cache the answer for 60 seconds. If GitHub is down, fall back to the last good answer instead of crashing.

---

## Step 3 — Store data with SQLite

We want AI review history to survive restarts. **SQLite** is a single-file database built into Python — no server to install.

### 3a. `backend/db.py`

```python
import sqlite3, os, json, time

DB_PATH = os.environ.get("DB_PATH", "data/app.db")

def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commit_sha TEXT, branch TEXT, score INTEGER,
            summary TEXT, report TEXT, created_at INTEGER
        );
    """)
    conn.commit(); conn.close()

def save_review(commit_sha, branch, score, summary, report):
    conn = _connect()
    conn.execute(
        "INSERT INTO reviews (commit_sha, branch, score, summary, report, created_at) VALUES (?,?,?,?,?,?)",
        (commit_sha, branch, score, summary, json.dumps(report), int(time.time())),
    )
    conn.commit(); conn.close()

def get_reviews(limit=20):
    conn = _connect()
    rows = conn.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) | {"report": json.loads(r["report"])} for r in rows]
```

> **Concept: SQL.**
> SQL is a language for talking to databases. `INSERT` saves a row; `SELECT ... ORDER BY id DESC` gets the newest rows first. The `?` placeholders protect against **SQL injection** — never paste user input directly into a query string.

### 3b. Expose it over HTTP

Add a `GET /reviews` (read) and a `POST /reviews` (write) endpoint. The AI pipeline will `POST` reports here; the dashboard reads them.

```python
from pydantic import BaseModel

class ReviewIn(BaseModel):
    commit_sha: str = ""
    branch: str = "main"
    score: int
    summary: str = ""
    report: dict

@app.post("/reviews", status_code=201)
def post_review(review: ReviewIn):
    db.save_review(review.commit_sha, review.branch, review.score, review.summary, review.report)
    return {"ok": True}
```

> **Concept: pydantic models.**
> Pydantic validates the request body. If someone POSTs JSON without a `score`, FastAPI automatically returns a 422 error. Free input validation, no code needed.

---

## Step 4 — The AI reviewer

`ai-review/ai_review.py` is the heart of the project: it grades the project's own code.

### 4a. Static scoring (no AI needed)

Before calling the LLM, we score code with simple checks — each check is worth points (total 100):

```python
SIGNALS = {
    "no_todo":       (10, "No TODO/FIXME markers left in code"),
    "no_debug":      (10, "No stray debug print() calls in libraries"),
    "no_bare_except":(10, "No bare except: blocks"),
    "short_enough":  (10, "No files over 500 lines"),
    "functions":     (15, "Good number of small functions"),
    "typed":         (15, "Type hints / annotations used"),
    "documented":    (15, "Docstrings / comments present"),
    "no_long_lines": (15, "No lines over 100 characters"),
}
```

The scorer walks the `.py` files and checks each rule with regex and simple counts:

```python
for path in files:
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    todo += len(re.findall(r"\b(TODO|FIXME|XXX)\b", text))
    debug += len(re.findall(r"print\(", text))
    bare += len(re.findall(r"except\s*:", text))
    ...
```

> **Concept: static analysis.**
> "Static" means reading the code without running it. Tools like flake8 (which we use in CI) do exactly this — they find problems by pattern-matching text.

### 4b. The LLM review (Ollama)

Ollama runs an LLM **on your machine** — no API key, no cost. It exposes a local HTTP API at `http://localhost:11434`.

```python
resp = requests.post(
    "http://localhost:11434/api/generate",
    json={"model": "llama3:8b",
          "prompt": "Review this code. Return JSON with summary/issues/strengths: ...",
          "stream": False,
          "format": "json"},
    timeout=300,
)
```

We tell the model to return **valid JSON only** (`format: "json"`), which makes parsing reliable. The whole thing is wrapped in `try/except` so if Ollama isn't running, the pipeline still passes — the report just says "LLM review unavailable".

### 4c. Save and upload the report

```python
report = {"commit_sha": COMMIT_SHA, "branch": BRANCH, "score": score,
          "static": static, "llm": llm, "created_at": int(time.time())}
save_report(report)        # writes review.json + review.txt
upload(report)             # POSTs to the backend via BACKEND_URL
```

---

## Step 5 — Automate everything with GitHub Actions

**GitHub Actions** runs commands in a free virtual machine every time you push. You describe the steps in YAML.

> **Concept: YAML.**
> YAML is a way to write data (lists + key/value pairs) that's human-readable. Indentation matters — two spaces per level. No tabs!

`.github/workflows/ci.yml`:

```yaml
name: AI-LLM CICD PIPELINE

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4               # 1. get our code
      - uses: actions/setup-python@v5          # 2. install Python
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r backend/requirements-dev.txt
      - run: flake8 backend ai-review --max-line-length=120   # lint gate
      - run: pytest backend --cov=backend --cov-fail-under=60 # test gate

  ai-review:
    needs: quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: |
          curl -fsSL https://ollama.com/install.sh | sh
          nohup ollama serve &                  # start Ollama in background
          sleep 10
      - run: ollama pull llama3:8b
      - run: python ai-review/ai_review.py       # the AI review
        env:
          BACKEND_URL: ${{ secrets.BACKEND_URL }}
      - uses: actions/upload-artifact@v4        # save review.json/review.txt
        with:
          name: ai-review-report
          path: review.json review.txt
```

Three things worth calling out:

- **`needs: quality`** — the AI review job waits for lint/tests to pass first. This creates a *gate*: broken code never reaches the AI review.
- **`${{ secrets.BACKEND_URL }}`** — secrets are hidden values you set in GitHub → Settings → Secrets. The workflow reads them like this and never prints them.
- **`actions/upload-artifact`** — artifacts are downloadable files attached to a run, like review reports or coverage output.

We also added a step that comments the AI score back onto the commit using the `gh` command-line tool, which GitHub pre-installs:

```bash
gh api -X POST "repos/${{ github.repository }}/commits/${{ github.sha }}/comments" \
  -f body="🤖 AI Review: $SCORE/100 — full report in the ai-review-report artifact."
```

> **Concept: gates.**
> A quality gate is a rule that *blocks* the pipeline if a threshold isn't met. Ours: coverage below 60% or any flake8 error fails the `quality` job, which stops everything downstream.

---

## Step 6 — The frontend dashboard

Plain HTML/CSS/JS, no framework. Three files:

### 6a. `index.html` — the skeleton

```html
<header><h1>🚀 AI LLM CI/CD Dashboard</h1></header>
<div class="search-bar"><input id="search" onkeyup="filterData()"></div>
<section class="overview">...stat cards...</section>
<section id="reviews" class="container"></section>
<section id="history" class="container"></section>
<section id="runs" class="container"></section>
<script src="app.js"></script>
```

The `<section>`s start empty — JavaScript fills them.

### 6b. `app.js` — fetch + render

```js
const BACKEND_URL = window.BACKEND_URL || "https://ai-llm-cicd-project.onrender.com";

async function fetchJson(path) {
  const res = await fetch(BACKEND_URL + path);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

async function loadData() {
  try {
    const [status, reviewsData] = await Promise.all([
      fetchJson("/status"),
      fetchJson("/reviews"),
    ]);
    renderOverview(status);
    render(status, reviewsData.reviews || []);
  } catch (err) {
    // show a friendly error box + Retry button
  }
}
setInterval(loadData, 60000);  // refresh every minute
loadData();
```

> **Concept: async/await + fetch.**
> `fetch` asks a server for data without freezing the page. `await` says "pause here until the answer arrives". Without it, the UI would try to render data that hasn't loaded yet.

### 6c. `style.css` — the black + orange theme

```css
:root {
  --bg: #0d0d0d;          /* background    */
  --panel: #1a1a1a;       /* card color    */
  --border: #ffaa00;      /* orange accent */
  --text: #f5a623;        /* orange text   */
}
```

Score badges change color with score: ≥75 green, ≥50 amber, else red. A helper builds them:

```js
function scoreClass(score) {
  return score >= 75 ? "high" : score >= 50 ? "mid" : "low";
}
```

> **Concept: variables in CSS.**
> CSS custom properties (`--var`) are like constants. Change `--border` once and every card updates. This keeps a consistent theme with zero repetition.

---

## Step 7 — Docker

**Docker** packages the backend so it runs the same everywhere (laptop, Render, anyone else's machine).

`Dockerfile`:

```dockerfile
FROM python:3.11-slim        # start from a small Python image
WORKDIR /app                 # our home folder inside the container
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .                     # copy our code in
EXPOSE 8080
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

`0.0.0.0` means "listen on all network interfaces" — required so the outside world can reach it. Docker Desktop lets you build locally to test:

```bash
docker build -t ai-llm-cicd-app .
docker run -p 8080:8080 ai-llm-cicd-app
```

`COPY . .` would also copy our virtual environment — that's why we add a `.dockerignore`:

```dockerignore
.venv/
data/
__pycache__/
frontend/     # not needed in the backend image
```

> **Concept: containers.**
> A container is a mini-computer with only our app inside it. "It works on my machine" becomes "it works everywhere".

---

## Step 8 — Tests and quality gates

Tests lock in the behavior. `backend/test_main.py` uses FastAPI's `TestClient` to call the app like a real user:

```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

Real API calls in tests are slow and flaky, so we **mock** the GitHub client:

```python
def test_status_uses_github_data(monkeypatch):
    monkeypatch.setattr(github_client, "get_repo", lambda: FAKE_REPO)
    monkeypatch.setattr(github_client, "get_workflow_runs", lambda: FAKE_RUNS)
    r = client.get("/status")
    assert r.json()["source"] == "github"
```

> **Concept: mocking.**
> A mock is a stand-in that returns fake data, so the test never touches the network. The test verifies *our logic*, not GitHub.

Run locally:

```bash
.venv/bin/python -m pytest backend --cov=backend --cov-fail-under=60
.venv/bin/flake8 backend ai-review --max-line-length=120 --exclude=backend/__init__.py
```

Current state: **8 tests, ~89% coverage**, flake8 clean. The same commands run in CI on every push.

---

## Step 9 — Deploy

### Backend → Render (free)

1. Push everything to GitHub.
2. At render.com: **New → Web Service → connect the repo**.
3. Service type: **Docker** (Render uses our `Dockerfile`).
4. Deploy. Set `GH_TOKEN` and `DB_PATH` in the Render env vars.
5. Copy the URL (e.g. `https://your-app.onrender.com`) and set it as the **`BACKEND_URL` secret** in GitHub → Settings → Secrets.

### Frontend → Cloudflare Pages (free)

1. Cloudflare dashboard → **Pages → Create a project → connect the repo**.
2. Build settings: build directory `/frontend`.
3. Deploy. Every push to main re-deploys automatically.

### The full loop after that

```
push to main
   │
   ▼
GitHub Actions
   ├─ lint + coverage gates  ──▶ fail = stop
   ├─ AI review (Ollama)     ──▶ review.json + commit comment
   └─ Docker build           ──▶ ready for Render
   │
   ▼
Backend updates on Render ──▶ dashboard shows new status + review
```

---

## The big picture

A beginner-friendly checklist of the concepts you just learned:

| Concept | Where it lives |
| --- | --- |
| HTTP APIs & JSON | `backend/main.py` |
| CORS | `backend/main.py` |
| REST endpoints (GET/POST) | `/status`, `/reviews`, `/health` |
| Caching & fallbacks | `cached()` in `backend/main.py` |
| SQL & SQLite | `backend/db.py` |
| Input validation | pydantic `ReviewIn` |
| Static code analysis | `ai-review/ai_review.py` + flake8 |
| LLM integration (Ollama) | `ai-review/ai_review.py` |
| CI/CD pipelines (YAML) | `.github/workflows/ci.yml` |
| Quality gates | flake8 + `--cov-fail-under=60` |
| Secrets | `${{ secrets.BACKEND_URL }}` |
| Frontend fetching & rendering | `frontend/app.js` |
| Containers | `Dockerfile` + `.dockerignore` |
| Automated testing & mocking | `backend/test_main.py` |

**Common beginner pitfalls we hit and fixed:**

- `allow_credentials=True` broke CORS with `"*"` → removed it.
- Module imports failed because `backend/` wasn't a package → added `backend/__init__.py` and used `from backend import ...`.
- Tests ordering broke because DB timestamps tied → order by `id DESC` instead.
- Scores always low until `short_enough` was initialized to `True` → always give a sane default.
- `uvicorn backend.main:app` needs to run from the repo root → run it with the project folder as the working directory.

That's the whole journey. Build it step by step, commit after every step, and watch GitHub do the work for you.
