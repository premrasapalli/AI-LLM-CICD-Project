import os
import tempfile

tmpdir = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(tmpdir, "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from backend import github_client, db, main as app_module  # noqa: E402

app = app_module.app
client = TestClient(app)

FAKE_REPO = {
    "name": "AI-LLM-CICD-Project",
    "full_name": "premrasapalli/AI-LLM-CICD-Project",
    "description": "test",
    "language": "Python",
    "stargazers_count": 3,
    "forks_count": 1,
    "open_issues_count": 2,
    "default_branch": "main",
    "updated_at": "2026-01-01T00:00:00Z",
}

FAKE_RUNS = {
    "workflow_runs": [
        {
            "id": 123,
            "name": "CI",
            "status": "completed",
            "conclusion": "success",
            "head_sha": "abc1234",
            "head_branch": "main",
            "html_url": "https://github.com/x/y/actions/runs/123",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
}


def test_home():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    assert "endpoints" in body


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_status_uses_github_data(monkeypatch):
    monkeypatch.setattr(github_client, "get_repo", lambda: FAKE_REPO)
    monkeypatch.setattr(github_client, "get_workflow_runs", lambda: FAKE_RUNS)
    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "github"
    assert body["project"] == "AI-LLM-CICD-Project"
    assert body["stars"] == 3
    assert body["runs"][0]["conclusion"] == "success"


def test_status_falls_back_to_stored(monkeypatch):
    app_module._cache.clear()
    monkeypatch.setattr(github_client, "get_repo", lambda: (_ for _ in ()).throw(Exception("offline")))
    monkeypatch.setattr(github_client, "get_workflow_runs", lambda: (_ for _ in ()).throw(Exception("offline")))
    db.save_review("sha", "main", 85, "looks good", {"issues": []})
    r = client.get("/status")
    body = r.json()
    assert body["source"] == "stored"
    assert body["latest_review"]["score"] == 85


def test_reviews_roundtrip():
    db.save_review("abc", "main", 90, "great", {"issues": ["minor"]})
    r = client.get("/reviews")
    body = r.json()
    assert len(body["reviews"]) >= 1
    assert body["reviews"][0]["report"]["issues"] == ["minor"]


def test_ci_runs_stored():
    db.save_ci_runs(FAKE_RUNS["workflow_runs"])
    r = client.get("/ci-runs")
    body = r.json()
    assert any(run["run_id"] == 123 for run in body["runs"])
