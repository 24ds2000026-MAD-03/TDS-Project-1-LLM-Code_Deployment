from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os, subprocess, tempfile, uuid, html
from datetime import datetime

# Load environment variables
load_dotenv()

# --- FastAPI Setup ---
app = FastAPI(title="LLM Code Deployment API")

# --- Environment Variables ---
STORED_SECRET = os.getenv("STORED_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
WORK_DIR = os.getenv("WORK_DIR", "./workspace")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Validations ---
if not STORED_SECRET:
    raise RuntimeError("STORED_SECRET not set in .env")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN not set in .env")
if not GITHUB_USERNAME:
    raise RuntimeError("GITHUB_USERNAME not set in .env")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in .env")

os.makedirs(WORK_DIR, exist_ok=True)

# --- LLM Code Generator ---
def generate_app_from_brief(brief: str) -> str:
    """Uses an LLM (OpenAI GPT-5) to generate minimal app code."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    You are an expert web developer.
    Generate a minimal but functional HTML/JS/CSS application
    that fulfills this brief:

    {brief}

    Requirements:
    - Must be self-contained in a single HTML file
    - Include minimal inline JS and CSS
    - Use clean and professional structure
    - Display meaningful content or interactivity per the brief
    """

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": "You are a skilled web app generator."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500
    )

    return response.choices[0].message.content.strip()


# --- API Endpoint ---
@app.post("/api-endpoint")
async def handle_request(request: Request):
    """Handles incoming POST requests from instructor evaluation."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # --- Secret Verification ---
    if data.get("secret") != STORED_SECRET:
        return JSONResponse({"error": "Invalid secret"}, status_code=403)

    # --- Extract Fields ---
    email = html.escape(data.get("email", "student@example.com"))
    task = html.escape(data.get("task", f"task-{uuid.uuid4().hex[:6]}"))
    round_ = int(data.get("round", 1))
    nonce = data.get("nonce")
    brief = data.get("brief", "")
    evaluation_url = data.get("evaluation_url", "")
    attachments = data.get("attachments", [])

    # --- Prepare Repo ---
    repo_name = f"{task}-{round_}".replace(" ", "-").lower()
    repo_path = os.path.join(WORK_DIR, repo_name)
    os.makedirs(repo_path, exist_ok=True)

    # --- Generate App with LLM ---
    print(f"🤖 Generating code for: {task}")
    try:
        generated_code = generate_app_from_brief(brief)
    except Exception as e:
        return JSONResponse({"error": f"LLM generation failed: {e}"}, status_code=500)

    # --- Write Files ---
    with open(os.path.join(repo_path, "index.html"), "w", encoding="utf-8") as f:
        f.write(generated_code)

    with open(os.path.join(repo_path, "README.md"), "w") as f:
        f.write(f"# {task}\n\n{brief}\n\nAuto-generated for {email} (Round {round_}).")

    with open(os.path.join(repo_path, "LICENSE"), "w") as f:
        f.write("MIT License\n\nCopyright (c) 2025\n\nPermission is hereby granted...")

    # --- Git Setup ---
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "AutoBot"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", email], cwd=repo_path, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", f"Initial commit for {task}"], cwd=repo_path, check=True)

    # --- GitHub Repo Creation ---
    repo_url = f"https://github.com/{GITHUB_USERNAME}/{repo_name}"
    subprocess.run([
        "gh", "repo", "create", repo_name,
        "--public", "--source", repo_path, "--push", "--confirm"
    ], check=True)

    # --- Enable GitHub Pages ---
    subprocess.run([
        "gh", "api", f"repos/{GITHUB_USERNAME}/{repo_name}/pages",
        "-f", "source.branch=main",
        "-f", "source.path=/"
    ], check=True)

    # --- Metadata ---
    commit_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_path
    ).decode().strip()
    pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"

    response_payload = {
        "email": email,
        "task": task,
        "round": round_,
        "nonce": nonce,
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url,
    }

    # --- Notify Evaluation Server ---
    if evaluation_url:
        try:
            import requests, time
            for delay in [1, 2, 4, 8, 16]:
                r = requests.post(
                    evaluation_url,
                    headers={"Content-Type": "application/json"},
                    json=response_payload,
                    timeout=10
                )
                if r.status_code == 200:
                    break
                time.sleep(delay)
        except Exception as e:
            print("⚠️ Evaluation callback failed:", e)

    return JSONResponse(response_payload, status_code=200)


# --- Run Command ---
# uvicorn main:app --reload
