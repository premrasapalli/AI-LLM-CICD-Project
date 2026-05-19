import requests

def review():
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3:8b",
                "prompt": "Review this project for best practices",
                "stream": False
            },
            timeout=120
        )
        print("AI Review:", response.json()["response"])
    except Exception as e:
        print("AI skipped:", str(e))

if __name__ == "__main__":
    review()
