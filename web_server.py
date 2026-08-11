# -*- coding: utf-8 -*-
"""
web_server.py — ShadowPlane Event-Driven CI/CD Gateway
======================================================
Production-grade FastAPI server that:
  1. Receives GitHub pull_request webhooks at POST /webhook
  2. Queues jobs in an asyncio.Queue (one-at-a-time worker prevents TF state locks)
  3. Streams real-time execution events to the Web UI via WebSocket /ws
  4. Posts a verification report back to the originating PR via GitHub REST API
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Set

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Resolve project root so we can import demo_loop and server
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
import demo_loop  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("ShadowPlane-WebServer")

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

def _env(key: str, default: str = "") -> str:
    """Read a config value from os.environ (already populated by server.py's load_env_file)."""
    return os.environ.get(key, default)

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
connected_clients: Set[WebSocket] = set()


async def broadcast(event_dict: dict):
    """Send a JSON event to every connected WebSocket client."""
    payload = json.dumps(event_dict)
    stale: list[WebSocket] = []
    for ws in connected_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        connected_clients.discard(ws)


# ---------------------------------------------------------------------------
# Job queue & background worker
# ---------------------------------------------------------------------------
job_queue: asyncio.Queue = asyncio.Queue()


async def background_worker():
    """
    Continuously process jobs from the queue, one at a time.
    This serialisation prevents Terraform state lock conflicts.
    """
    logger.info("Background worker started — waiting for jobs...")
    while True:
        job = await job_queue.get()
        logger.info("Worker picked up job: PR #%s on %s/%s", job["pr_number"], job["repo"], job["branch"])

        # Notify all clients that a new job is starting
        await broadcast({
            "type": "job",
            "repo": job["repo"],
            "branch": job["branch"],
            "pr_number": job["pr_number"],
            "sender": job["sender"],
        })

        # Capture the original and patched content for the PR comment
        original_tf = None
        patched_tf = None
        diff_message = ""
        success = False

        # Wrap broadcast to also capture diff events
        async def yield_event(event_dict):
            nonlocal original_tf, patched_tf, diff_message
            if event_dict.get("type") == "diff":
                original_tf = event_dict.get("original", "")
                patched_tf = event_dict.get("patched", "")
                diff_message = event_dict.get("message", "")
            await broadcast(event_dict)

        try:
            await demo_loop.main(yield_event=yield_event)
            success = True
            await broadcast({"type": "done"})
        except Exception as e:
            logger.error("Job failed for PR #%s: %s", job["pr_number"], e)
            await broadcast({"type": "log", "level": "error", "content": str(e)})
            await broadcast({"type": "error"})

        # Post feedback to GitHub PR
        await post_pr_comment(
            repo=job["repo"],
            pr_number=job["pr_number"],
            success=success,
            original_tf=original_tf,
            patched_tf=patched_tf,
            diff_message=diff_message,
        )

        job_queue.task_done()
        logger.info("Job completed for PR #%s (success=%s)", job["pr_number"], success)


# ---------------------------------------------------------------------------
# GitHub API: Post PR comment
# ---------------------------------------------------------------------------
async def post_pr_comment(
    repo: str,
    pr_number: int,
    success: bool,
    original_tf: str | None,
    patched_tf: str | None,
    diff_message: str,
):
    """Post a verification report comment on the originating Pull Request."""
    token = _env("GITHUB_TOKEN")
    if not token or token == "your_github_pat_here":
        logger.warning("GITHUB_TOKEN not configured — skipping PR comment for PR #%s", pr_number)
        return

    status_emoji = "✅" if success else "❌"
    status_text = "Passed" if success else "Failed"

    body = f"""## {status_emoji} ShadowPlane Autonomous Verification Report

**Status**: {status_text}
**Repository**: `{repo}`
**Pull Request**: #{pr_number}

"""
    if success and original_tf and patched_tf:
        body += f"""### Self-Healing Applied
> {diff_message}

<details>
<summary>View patched <code>main.tf</code> diff</summary>

```diff
"""
        # Build a simple line-by-line diff
        orig_lines = original_tf.splitlines()
        patch_lines = patched_tf.splitlines()
        max_len = max(len(orig_lines), len(patch_lines))
        for i in range(max_len):
            o = orig_lines[i] if i < len(orig_lines) else ""
            p = patch_lines[i] if i < len(patch_lines) else ""
            if o != p:
                if o:
                    body += f"- {o}\n"
                if p:
                    body += f"+ {p}\n"
            else:
                body += f"  {o}\n"

        body += """```

</details>

---
*ShadowPlane intercepted a deployment error, isolated the blast radius in a LocalStack sandbox, and autonomously repaired the infrastructure code.*
"""
    elif not success:
        body += """### Failure Details
The autonomous repair loop was unable to resolve the infrastructure error within the maximum retry limit.
Please review the Terraform logs and fix the issue manually.

---
*ShadowPlane intercepted a deployment error but could not auto-repair it.*
"""

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={"body": body}, headers=headers)
            if resp.status_code in (200, 201):
                logger.info("Posted verification comment on PR #%s", pr_number)
            else:
                logger.warning(
                    "GitHub API returned %s for PR #%s: %s",
                    resp.status_code, pr_number, resp.text[:200],
                )
    except Exception as e:
        logger.error("Failed to post PR comment: %s", e)


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------
def verify_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """Verify the X-Hub-Signature-256 header against the webhook secret."""
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# FastAPI app with lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background worker on server startup."""
    worker_task = asyncio.create_task(background_worker())
    logger.info("ShadowPlane Web Server starting up...")
    yield
    worker_task.cancel()
    logger.info("ShadowPlane Web Server shutting down.")


app = FastAPI(title="ShadowPlane Gateway", lifespan=lifespan)

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main Web UI."""
    with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/webhook")
async def webhook(request: Request):
    """
    Receive GitHub pull_request webhook events.
    Validates signature, parses PR metadata, and enqueues a job.
    """
    body = await request.body()

    # Signature verification (skip if no secret is configured — dev mode)
    secret = _env("GITHUB_WEBHOOK_SECRET")
    if secret and secret != "your_webhook_secret_here":
        signature = request.headers.get("X-Hub-Signature-256")
        if not verify_signature(body, signature, secret):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

    # Only process pull_request events
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"Event type '{event_type}' is not handled"}

    payload = json.loads(body)
    action = payload.get("action", "")

    # Only trigger on opened, synchronize (new push), or reopened
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "reason": f"Action '{action}' is not handled"}

    pr = payload.get("pull_request", {})
    pr_number = pr.get("number", 0)
    head = pr.get("head", {})
    branch = head.get("ref", "unknown")
    repo_info = head.get("repo", {})
    repo = repo_info.get("full_name", "unknown/unknown")
    sender = payload.get("sender", {}).get("login", "unknown")

    job = {
        "repo": repo,
        "branch": branch,
        "pr_number": pr_number,
        "sender": sender,
    }

    await job_queue.put(job)
    queue_depth = job_queue.qsize()
    logger.info("Enqueued job for PR #%s (%s@%s) — queue depth: %d", pr_number, repo, branch, queue_depth)

    # Notify connected clients about the queue update
    await broadcast({"type": "queue", "depth": queue_depth})

    return {"status": "queued", "pr_number": pr_number, "queue_depth": queue_depth}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for real-time event streaming to the frontend."""
    await ws.accept()
    connected_clients.add(ws)
    logger.info("WebSocket client connected. Total clients: %d", len(connected_clients))
    try:
        while True:
            # Keep the connection alive; we don't expect inbound messages
            # but we need to read to detect disconnects
            await ws.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(ws)
        logger.info("WebSocket client disconnected. Total clients: %d", len(connected_clients))
    except Exception:
        connected_clients.discard(ws)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
