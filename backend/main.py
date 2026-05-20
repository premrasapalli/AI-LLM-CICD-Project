from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check
@app.get("/")
def home():
    return {"message": "AI LLM CI/CD Backend Running 🚀"}

# ✅ Main dashboard API
@app.get("/status")
def get_status():
    return [
        {
            "project": "ai-llm-cicd-project",
            "status": "Deployed",
            "build": "Success",
            "ai_review": "Code quality is good. CI/CD pipeline working correctly."
        },
        {
            "project": "ai-llm-cicd-project",
            "status": "Deployed",
            "build": "Success",
            "ai_review": "No major issues found. Code is clean and optimized."
        },
        {
            "project": "ai-llm-cicd-project",
            "status": "Pending",
            "build": "Running",
            "ai_review": "AI review in progress..."
        }
    ]
