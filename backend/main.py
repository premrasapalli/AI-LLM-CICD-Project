import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend import github_client, db

app = FastAPI(title="AI LLM CI/CD Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

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
        return entry[1] if entry else None


@app.get("/")
def home():
    return {
        "message": "AI LLM CI/CD Backend Running 🚀",
        "repo": f"{github_client.OWNER}/{github_client.REPO}",
        "endpoints": ["/status", "/reviews", "/ci-runs", "/health"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def get_status():
    repo = cached("repo", github_client.get_repo)
    runs = cached("runs", github_client.get_workflow_runs)

    if runs:
        try:
            db.save_ci_runs(runs.get("workflow_runs", [])[:10])
        except Exception:
            pass

    latest_run = None
    run_data = []
    if runs:
        run_data = [
            {
                "id": r.get("id"),
                "name": r.get("name", ""),
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "head_sha": (r.get("head_sha") or "")[:7],
                "branch": r.get("head_branch"),
                "url": r.get("html_url"),
                "created_at": r.get("created_at"),
            }
            for r in runs.get("workflow_runs", [])[:10]
        ]
        latest_run = run_data[0] if run_data else None

    latest_review = None
    reviews = []
    try:
        reviews = db.get_reviews(limit=1)
        if reviews:
            latest_review = reviews[0]
    except Exception:
        pass

    if repo:
        return {
            "project": repo.get("name"),
            "full_name": repo.get("full_name"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "default_branch": repo.get("default_branch"),
            "updated_at": repo.get("updated_at"),
            "latest_run": latest_run,
            "runs": run_data,
            "latest_review": latest_review,
            "source": "github",
        }

    if latest_review:
        return {
            "project": f"{github_client.OWNER}/{github_client.REPO}",
            "source": "stored",
            "latest_review": latest_review,
            "note": "GitHub API unavailable - showing last stored review.",
        }

    return {
        "project": f"{github_client.OWNER}/{github_client.REPO}",
        "source": "unavailable",
        "note": "GitHub API unavailable and no stored data yet. Run the pipeline once.",
    }


@app.get("/reviews")
def get_reviews(limit: int = 20):
    try:
        return {"reviews": db.get_reviews(limit=limit)}
    except Exception as e:
        return {"reviews": [], "error": str(e)}


class ReviewIn(BaseModel):
    commit_sha: str = ""
    branch: str = "main"
    score: int
    summary: str = ""
    report: dict


@app.post("/reviews", status_code=201)
def post_review(review: ReviewIn):
    db.save_review(review.commit_sha, review.branch, review.score, review.summary, review.report)
    return {"ok": True, "id": db.get_reviews(limit=1)[0]["id"]}


@app.get("/ci-runs")
def get_ci_runs(limit: int = 20):
    try:
        return {"runs": db.get_ci_runs(limit=limit)}
    except Exception as e:
        return {"runs": [], "error": str(e)}
