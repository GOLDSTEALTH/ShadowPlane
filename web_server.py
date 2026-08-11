import asyncio
import json
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import our autonomous loop
import demo_loop

app = FastAPI()

# Mount static files (CSS, JS)
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# Global event queue for SSE
# In a real app, this would be per-client or handled via a proper pub/sub
event_queue = None

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main Web UI."""
    with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/start")
async def start_loop():
    """Endpoint to trigger the autonomous loop."""
    global event_queue
    event_queue = asyncio.Queue()
    
    # Callback passed to demo_loop to stream events back to the UI
    async def yield_event(event_dict):
        if event_queue:
            await event_queue.put(event_dict)

    # Run the loop in a background task
    asyncio.create_task(run_demo_and_close(yield_event))
    return {"status": "started"}

async def run_demo_and_close(yield_event):
    """Wrapper to run the demo and then signal completion."""
    try:
        await demo_loop.main(yield_event=yield_event)
        await yield_event({"type": "done"})
    except Exception as e:
        await yield_event({"type": "log", "level": "error", "content": str(e)})
        await yield_event({"type": "error"})

@app.get("/api/stream")
async def stream():
    """SSE endpoint consumed by the frontend."""
    async def event_generator():
        global event_queue
        if not event_queue:
            return
            
        while True:
            try:
                event = await event_queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("done", "error"):
                    break
            except asyncio.CancelledError:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
