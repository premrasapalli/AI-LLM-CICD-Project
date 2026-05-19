const API_URL = "https://your-render-url.onrender.com";
async function callAPI() {
  const res = await fetch(API_URL);
  const data = await res.json();
  document.getElementById("output").innerText =
    JSON.stringify(data, null, 2);
}
