import json
import os
import re
import sys
import time
import urllib.request

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3:8b")
BACKEND_URL = os.environ.get("BACKEND_URL", "").rstrip("/")
ROOT = os.environ.get("REVIEW_ROOT", os.getcwd())
COMMIT_SHA = os.environ.get("GITHUB_SHA", "")[:7]
BRANCH = os.environ.get("GITHUB_HEAD_REF", os.environ.get("GITHUB_REF_NAME", "main"))

# Static quality signals (weights sum to 100)
SIGNALS = {
    "no_todo": (10, "No TODO/FIXME markers left in code"),
    "no_debug": (10, "No stray debug print() calls in libraries"),
    "no_bare_except": (10, "No bare except: blocks"),
    "short_enough": (10, "Files are reasonably sized (no > 500-line files)"),
    "functions": (15, "Good number of small functions defined"),
    "typed": (15, "Type hints / annotations used"),
    "documented": (15, "Docstrings / comments present"),
    "no_long_lines": (15, "No lines over 100 characters"),
}


def _py_files():
    found = []
    for root, _, files in os.walk(ROOT):
        if any(part.startswith(".") for part in root.split(os.sep)):
            continue
        if ".venv" in root or "node_modules" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                found.append(os.path.join(root, file))
    return sorted(found)


def get_code(files, limit=14000):
    code = ""
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                code += f"\n# FILE: {path}\n" + f.read()
        except Exception:
            pass
        if len(code) >= limit:
            break
    return code[:limit]


def static_score(files):
    checks = {}
    checks["short_enough"] = True
    todo = debug = bare = long_lines = 0
    total_lines = 0
    has_hints = has_docstrings = False
    funcs = 0

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        lines = text.splitlines()
        total_lines += len(lines)
        if len(lines) > 500:
            checks["short_enough"] = False
        todo += len(re.findall(r"\b(TODO|FIXME|XXX)\b", text))
        debug += len(re.findall(r"print\(", text))
        bare += len(re.findall(r"except\s*:", text))
        long_lines += sum(1 for line in lines if len(line) > 100)
        if re.search(r"def\s+\w+\([^)]*\)\s*->", text):
            has_hints = True
        if re.search(r"\"\"\"|'''", text):
            has_docstrings = True
        funcs += len(re.findall(r"^\s*def\s+\w+", text, re.M))

    checks["no_todo"] = todo == 0
    checks["no_debug"] = debug == 0
    checks["no_bare_except"] = bare == 0
    checks["no_long_lines"] = long_lines == 0
    checks["functions"] = funcs >= 2
    checks["typed"] = has_hints
    checks["documented"] = has_docstrings

    score = 0
    breakdown = []
    for name, (weight, label) in SIGNALS.items():
        ok = checks.get(name, False)
        if ok:
            score += weight
        breakdown.append({"check": name, "label": label, "pass": ok, "points": weight if ok else 0})

    if total_lines == 0:
        score = 0

    return {
        "score": score,
        "files": len(files),
        "lines": total_lines,
        "todo_markers": todo,
        "debug_prints": debug,
        "bare_excepts": bare,
        "long_lines": long_lines,
        "functions": funcs,
        "typed": has_hints,
        "documented": has_docstrings,
        "checks": breakdown,
    }


def llm_review(code):
    prompt = f"""
You are a senior software engineer. Review this code and return a compact JSON object with exactly these keys:
{{"summary": "one sentence", "issues": ["..."], "strengths": ["..."]}}

Rules:
- Keep issues and strengths to at most 3 short items each.
- Only output valid JSON, nothing else.

CODE:
{code}
"""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=300,
        )
        data = resp.json()
        return json.loads(data.get("response", "{}"))
    except Exception as e:
        return {"summary": f"LLM review unavailable: {e}", "issues": [], "strengths": []}


def save_report(report, review_path="review.json", txt_path="review.txt"):
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(_format_text(report))


def _format_text(report):
    stat = report["static"]
    lines = []
    lines.append("AI CODE REVIEW REPORT")
    lines.append("=" * 60)
    lines.append(f"Commit:    {report.get('commit_sha', '')}")
    lines.append(f"Branch:    {report.get('branch', '')}")
    lines.append(f"Files:     {stat.get('files', 0)}")
    lines.append(f"Lines:     {stat.get('lines', 0)}")
    lines.append(f"AI Score:  {report.get('score')}/100")
    lines.append("")
    lines.append("Static checks:")
    for c in stat.get("checks", []):
        lines.append(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['label']}")
    llm = report.get("llm", {})
    if llm.get("summary"):
        lines.append("")
        lines.append("LLM summary:")
        lines.append("  " + llm["summary"])
    if llm.get("issues"):
        lines.append("")
        lines.append("Issues:")
        for i in llm["issues"]:
            lines.append(f"  - {i}")
    if llm.get("strengths"):
        lines.append("")
        lines.append("Strengths:")
        for s in llm["strengths"]:
            lines.append(f"  + {s}")
    return "\n".join(lines) + "\n"


def upload(report):
    if not BACKEND_URL:
        print("  → no BACKEND_URL set, skipping upload")
        return
    payload = {
        "commit_sha": report.get("commit_sha", ""),
        "branch": report.get("branch", ""),
        "score": report.get("score", 0),
        "summary": report.get("llm", {}).get("summary", ""),
        "report": report,
    }
    try:
        req = urllib.request.Request(
            f"{BACKEND_URL}/reviews",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"  → uploaded to backend: {resp.status}")
    except Exception as e:
        print(f"  ⚠️ backend upload failed (non-fatal): {e}")


def main():
    start = time.time()
    files = _py_files()
    if not files:
        print("⚠️ No Python files found")
        sys.exit(0)

    code = get_code(files)
    static = static_score(files)
    llm = llm_review(code) if code.strip() else {}
    score = static["score"]

    report = {
        "commit_sha": COMMIT_SHA,
        "branch": BRANCH,
        "score": score,
        "static": static,
        "llm": llm,
        "created_at": int(time.time()),
        "duration_sec": round(time.time() - start, 1),
    }

    save_report(report)
    print(_format_text(report))
    upload(report)


if __name__ == "__main__":
    main()
