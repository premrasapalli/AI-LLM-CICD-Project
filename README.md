# AI-LLM-CICD-Project

Real-world DevOps + AI system: a FastAPI backend, a GitHub Actions CI/CD pipeline, an Ollama-powered AI code reviewer, and a live dashboard.

- Frontend → Cloudflare Pages (static dashboard)
- Backend → Render (FastAPI + SQLite)
- CI/CD → GitHub Actions
- AI Review → Ollama (local LLM)

## Project structure

```
AI-LLM-CICD-Project/
│
├── backend/
│   ├── main.py              # FastAPI app (status, reviews, ci-runs, health)
│   ├── github_client.py     # GitHub API client (stdlib urllib)
│   ├── db.py                # SQLite storage for reviews + CI runs
│   ├── test_main.py         # pytest suite
│   ├── requirements.txt     # runtime deps
│   └── requirements-dev.txt # test/lint deps
│
├── ai-review/
│   └── ai_review.py         # static scoring (0-100) + Ollama LLM review
│
├── frontend/
│   ├── index.html
│   ├── style.css            # black + orange theme
│   └── app.js               # fetches /status + /reviews, search filter
│
├── .github/workflows/ci.yml # lint, coverage gate, AI review, artifacts, commit comment
├── Dockerfile               # backend image
├── requirements.txt         # root runtime deps
└── runbook.md               # full build/run guide
```

## Backend API

| Endpoint | Method | Description |
| --- | --- | --- |
| `/` | GET | Service info + available endpoints |
| `/health` | GET | Health check |
| `/status` | GET | Live repo + latest CI run + latest AI review from the GitHub API (cached 60s) |
| `/reviews` | GET | Stored AI review history (SQLite) |
| `/reviews` | POST | Persist an AI review report (used by the pipeline) |
| `/ci-runs` | GET | Stored CI workflow runs |

### Environment variables (backend)

| Variable | Default | Purpose |
| --- | --- | --- |
| `GH_OWNER` | `premrasapalli` | GitHub owner for the API data source |
| `GH_REPO` | `AI-LLM-CICD-Project` | GitHub repo for the API data source |
| `GH_TOKEN` | `` | GitHub token (optional; avoids rate limits) |
| `DB_PATH` | `data/app.db` | SQLite database location |

## AI review scoring

`ai-review/ai_review.py` computes a static quality score out of 100 and calls Ollama for an LLM summary:

- No TODO/FIXME markers (10)
- No stray debug `print()` calls (10)
- No bare `except:` blocks (10)
- No files over 500 lines (10)
- Small functions defined (15)
- Type hints used (15)
- Docstrings/comments present (15)
- No lines over 100 characters (15)

It writes `review.json` + `review.txt`, uploads the report to the backend (`BACKEND_URL` env), and is safe to run without Ollama running.

```
python ai-review/ai_review.py
```

## CI/CD pipeline

`.github/workflows/ci.yml` runs three jobs on every push/PR to `main`:

1. **Quality gates** — `flake8` linting and `pytest --cov-fail-under=60` (coverage gate)
2. **AI review** — installs Ollama, pulls `llama3:8b`, runs the reviewer, uploads the report as an artifact, and posts the score as a commit comment
3. **Docker build** — builds the backend image

> Set the **`BACKEND_URL`** repo secret (e.g. `https://your-app.onrender.com`) so CI can upload review reports.

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r backend/requirements-dev.txt

# Run tests + lint
.venv/bin/python -m pytest backend --cov=backend --cov-fail-under=60
.venv/bin/flake8 backend ai-review --max-line-length=120 --exclude=backend/__init__.py

# Run the backend
.venv/bin/uvicorn backend.main:app --reload --port 8000

# Serve the dashboard (point app.js BACKEND_URL at http://localhost:8000)
cd frontend && python3 -m http.server 8080
```

## Deployment

- **Backend → Render**: connect the repo, service type Docker, deploy. Optionally set `GH_TOKEN` and `DB_PATH`.
- **Frontend → Cloudflare Pages**: connect the repo, build directory `/frontend`, deploy.

## Troubleshooting

- **AI review fails** → is Ollama running (`ollama serve`) and the model pulled (`ollama pull llama3:8b`)?
- **CORS errors in dashboard** → backend must allow the dashboard origin; local API is `http://localhost:8000`.
- **Rate limited GitHub API** → set `GH_TOKEN`.
