from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "AI-LLM CICD APP Backend Running 🚀"}
