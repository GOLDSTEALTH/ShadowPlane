import asyncio
import httpx
import time

async def trigger_webhook(client: httpx.AsyncClient, pr_number: int):
    """Simulates a GitHub pull_request webhook payload."""
    payload = {
        "action": "opened",
        "pull_request": {
            "number": pr_number,
            "head": {
                "ref": f"feature/dev-{pr_number}",
                "repo": {"full_name": "GOLDSTEALTH/ShadowPlane"}
            }
        },
        "sender": {"login": f"DevUser{pr_number}"}
    }
    headers = {
        "X-GitHub-Event": "pull_request",
        "Content-Type": "application/json"
    }
    
    start = time.monotonic()
    response = await client.post("http://localhost:8000/webhook", json=payload, headers=headers)
    elapsed = (time.monotonic() - start) * 1000
    
    print(f"PR #{pr_number:03d} -> Status: {response.status_code} | Queue Depth: {response.json().get('queue_depth')} | Time: {elapsed:.1f}ms")


async def main():
    print("=========================================================")
    print(" ShadowPlane Concurrency Test: 8 Simultaneous Webhooks   ")
    print("=========================================================")
    
    # We will simulate PRs #101 through #108
    pr_numbers = list(range(101, 109))
    
    async with httpx.AsyncClient() as client:
        # Fire them all off concurrently using asyncio.gather
        tasks = [trigger_webhook(client, pr) for pr in pr_numbers]
        await asyncio.gather(*tasks)
        
    print("=========================================================")
    print(" All webhook payloads delivered successfully!            ")
    print(" Check the web server logs and UI to watch the queue.    ")
    print("=========================================================")

if __name__ == "__main__":
    asyncio.run(main())
