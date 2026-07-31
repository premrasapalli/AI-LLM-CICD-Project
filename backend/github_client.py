import json
import os
import urllib.request

API = "https://api.github.com"
OWNER = os.environ.get("GH_OWNER", "premrasapalli")
REPO = os.environ.get("GH_REPO", "AI-LLM-CICD-Project")
TOKEN = os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN", ""))


def _get(path):
    url = f"{API}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def get_repo():
    return _get(f"/repos/{OWNER}/{REPO}")


def get_branches():
    return _get(f"/repos/{OWNER}/{REPO}/branches")


def get_latest_commits():
    return _get(f"/repos/{OWNER}/{REPO}/commits?per_page=10")


def get_workflow_runs():
    return _get(f"/repos/{OWNER}/{REPO}/actions/runs?per_page=10")
