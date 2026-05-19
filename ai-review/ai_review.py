import requests
import os

OLLAMA_URL = "http://localhost:11434/api/generate"


def get_code():
    code = ""

    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                try:
                    with open(os.path.join(root, file), "r") as f:
                        code += f"\n# File: {file}\n" + f.read()
                except:
                    pass

    return code


def review():
    try:
        code = get_code()

        if not code.strip():
            print("⚠️ No code found")
            return

        prompt = f"""
You are a senior software engineer.

Review the following FastAPI project and give:

1. Code quality feedback
2. Security issues
3. Performance improvements
4. Best practice suggestions

Code:
{code}
"""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3:8b",
                "prompt": prompt,
                "stream": False
            },
            timeout=300
        )

        result = response.json()

        print("\n✅ AI REVIEW RESULT:\n")
        print(result.get("response", "No response"))

    except Exception as e:
        print("⚠️ AI skipped:", str(e))


if __name__ == "__main__":
    review()
