const BACKEND_URL = window.BACKEND_URL || "https://ai-llm-cicd-project.onrender.com";

let allCards = [];

function $(id) { return document.getElementById(id); }

async function fetchJson(path) {
  const res = await fetch(BACKEND_URL + path);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

function scoreClass(score) {
  if (score >= 75) return "high";
  if (score >= 50) return "mid";
  return "low";
}

function buildBadge(conclusion, status) {
  const state = conclusion === "success" ? "success" : status === "completed" ? "fail" : "pending";
  const label = (conclusion || status).toUpperCase();
  return `<span class="badge ${state}">${label}</span>`;
}

function checkRows(checks) {
  if (!checks || !checks.length) return '<p class="muted">No static checks recorded.</p>';
  return checks
    .map(
      (c) =>
        `<div class="check-row"><span>${c.label}</span>` +
        `<span class="${c.pass ? "check-pass" : "check-fail"}">${c.pass ? "PASS" : "FAIL"}</span></div>`
    )
    .join("");
}

function reviewCard(r) {
  const score = r.score ?? 0;
  const checks = r.report?.static?.checks || [];
  const llm = r.report?.llm || {};
  const issues = (llm.issues || []).map((i) => `<li>${i}</li>`).join("");

  return `
    <div class="card review-card" data-search="${(r.summary || "") + " review " + (r.commit_sha || "")}">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3>🤖 AI Review${r.commit_sha ? ` <span class="muted">${r.commit_sha}</span>` : ""}</h3>
        <span class="score ${scoreClass(score)}">${score}/100</span>
      </div>
      <div class="scorebar"><div class="scorebar-fill" style="width:${score}%;background:${
        score >= 75 ? "var(--green)" : score >= 50 ? "var(--amber)" : "var(--red)"
      }"></div></div>
      ${r.summary ? `<p>${r.summary}</p>` : ""}
      <div class="chips">
        <span class="chip">${r.report?.static?.files ?? 0} files</span>
        <span class="chip">${r.report?.static?.lines ?? 0} lines</span>
        <span class="chip">branch: ${r.branch || "main"}</span>
      </div>
      <div>${checkRows(checks)}</div>
      ${issues ? `<ul class="review-list">${issues}</ul>` : ""}
    </div>
  `;
}

function runCard(run) {
  return `
    <div class="card run-card" data-search="${run.name + " " + (run.branch || "") + " " + (run.head_sha || "")}">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3>⚙️ ${run.name}</h3>
        ${buildBadge(run.conclusion, run.status)}
      </div>
      <p class="muted">
        ${run.branch || "?"} · ${run.head_sha || ""} ·
        ${run.created_at ? new Date(run.created_at).toLocaleString() : ""}
      </p>
      ${run.url ? `<p><a href="${run.url}" target="_blank" rel="noopener">View run ↗</a></p>` : ""}
    </div>
  `;
}

function renderOverview(status) {
  const r = status.latest_review || {};
  const lastRun = status.latest_run || {};
  const score = r.score ?? "—";
  const lines = r.report?.static?.lines ?? "—";

  $("stat-repo").querySelector(".stat-value").textContent = status.full_name || status.project || "—";
  $("stat-score").querySelector(".stat-value").textContent = typeof score === "number" ? score + "/100" : score;
  $("stat-last-build").querySelector(".stat-value").textContent = (lastRun.conclusion || lastRun.status || "—").toUpperCase();
  $("stat-lines").querySelector(".stat-value").textContent = lines;

  const note = document.createElement("span");
  if (status.note) note.textContent = status.note;
  if (status.source === "github" && status.updated_at) {
    note.textContent = `Data from GitHub API · updated ${new Date(status.updated_at).toLocaleString()}`;
  }
  $("source-note").innerHTML = "";
  $("source-note").appendChild(note);
}

function render(status, history) {
  const reviews = status.latest_review ? [status.latest_review] : [];
  const runs = status.runs || [];
  const past = history || [];

  $("reviews").innerHTML = `<h2>Latest AI Review</h2>` + (reviews.length ? reviews.map(reviewCard).join("") : '<div class="card muted">No AI review yet. Push to main to generate one.</div>');

  $("history").innerHTML =
    `<h2>Review History (${past.length})</h2>` +
    (past.length
      ? past.map(reviewCard).join("")
      : '<div class="card muted">No historical reviews stored in the backend yet.</div>');

  $("runs").innerHTML = `<h2>CI Runs</h2>` + (runs.length ? runs.map(runCard).join("") : '<div class="card muted">No CI runs yet.</div>');

  allCards = document.querySelectorAll(".card");
}

function filterData() {
  const value = $("search").value.toLowerCase();
  allCards.forEach((card) => {
    const hit = (card.dataset.search || "").toLowerCase().includes(value);
    card.style.display = hit ? "" : "none";
  });
}

async function loadData() {
  $("loading").textContent = "Loading project data...";
  try {
    const [status, reviewsData] = await Promise.all([fetchJson("/status"), fetchJson("/reviews")]);
    $("loading").style.display = "none";
    renderOverview(status);
    render(status, reviewsData.reviews || []);
  } catch (err) {
    $("loading").style.display = "none";
    const errBox = document.createElement("div");
    errBox.className = "error";
    errBox.innerHTML =
      `❌ Failed to load backend data at <b>${BACKEND_URL}</b><br><br>` +
      `<span class="muted">${err.message}</span><br><br>` +
      `<button onclick="loadData()">Retry</button>`;
    $("reviews").replaceWith(errBox);
    console.error(err);
  }
}

setInterval(loadData, 60000);
loadData();
