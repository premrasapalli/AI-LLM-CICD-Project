let projects = [];

// 🔥 Load data from backend
async function loadData() {
  try {
    const res = await fetch("https://ai-llm-cicd-project.onrender.com/status");
    const data = await res.json();

    projects = data;

    document.getElementById("loading").style.display = "none";
    render(projects);
  } catch (err) {
    document.getElementById("loading").innerText = "❌ Failed to load backend data";
    console.error(err);
  }
}

// 🎨 Render UI
function render(data) {
  const app = document.getElementById("app");
  app.innerHTML = "";

  if (data.length === 0) {
    app.innerHTML = "<p>No data found</p>";
    return;
  }

  data.forEach(item => {
    const buildClass = item.build === "Success" ? "status-success" : "status-fail";

    app.innerHTML += `
      <div class="card">
        <h2>${item.project}</h2>
        <p>🚀 Deployment: <span class="${buildClass}">${item.status}</span></p>
        <p>⚙️ Build: <span class="${buildClass}">${item.build}</span></p>
        <p>🤖 AI Review:</p>
        <p>${item.ai_review}</p>
      </div>
    `;
  });
}

// 🔍 Search filter
function filterData() {
  const value = document.getElementById("search").value.toLowerCase();

  const filtered = projects.filter(p =>
    p.project.toLowerCase().includes(value)
  );

  render(filtered);
}

// 🔁 Auto refresh
setInterval(loadData, 5000);

// 🚀 Initial load
loadData();
