"""FastAPI server exposing Steam Workshop API to the frontend."""

import json
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .api import browse_workshop, get_item_details, parse_workshop_id, get_api_key
from .downloader import find_steamcmd, stream_download, send_steamcmd_input, get_install_instructions

app = FastAPI(title="Steam Workshop Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class WorkshopItemOut(BaseModel):
    workshop_id: str
    title: str
    description: str
    app_id: str
    file_size: int
    size_human: str
    subscriptions: int
    favorited: int
    tags: list[str]
    preview_url: str
    workshop_url: str


class BrowseResponse(BaseModel):
    total: int
    items: list[WorkshopItemOut]
    has_api_key: bool


class DownloadRequest(BaseModel):
    app_id: str
    workshop_ids: list[str]
    output_dir: str = "./downloads"
    username: str = "anonymous"


class SteamGuardInput(BaseModel):
    code: str


def to_out(item) -> WorkshopItemOut:
    return WorkshopItemOut(
        workshop_id=item.workshop_id,
        title=item.title,
        description=item.description,
        app_id=item.app_id,
        file_size=item.file_size,
        size_human=item.size_human(),
        subscriptions=item.subscriptions,
        favorited=item.favorited,
        tags=item.tags,
        preview_url=item.preview_url,
        workshop_url=f"https://steamcommunity.com/sharedfiles/filedetails/?id={item.workshop_id}",
    )


@app.get("/api/browse", response_model=BrowseResponse)
async def browse(
    app_id: str = Query(..., description="Steam App ID"),
    sort: str = Query("trend", description="trend|top|new|favorites"),
    page: int = Query(1, ge=1),
    count: int = Query(20, ge=1, le=50),
    search: str = Query("", description="Search query"),
):
    sort_map = {"trend": 1, "top": 0, "new": 3, "favorites": 2}
    query_type = sort_map.get(sort, 1)
    try:
        loop = asyncio.get_event_loop()
        total, items = await loop.run_in_executor(
            None,
            lambda: browse_workshop(
                app_id,
                query_type=query_type,
                page=page,
                count=count,
                search_text=search,
                sort=sort,
            ),
        )
        return BrowseResponse(
            total=total,
            items=[to_out(i) for i in items],
            has_api_key=bool(get_api_key()),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/item/{workshop_id}", response_model=WorkshopItemOut)
async def get_item(workshop_id: str):
    wid = parse_workshop_id(workshop_id)
    if not wid:
        raise HTTPException(status_code=400, detail="Invalid workshop ID")
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(None, lambda: get_item_details([wid]))
    if not items:
        raise HTTPException(status_code=404, detail="Item not found")
    return to_out(items[0])


@app.post("/api/download/stream")
async def download_stream(req: DownloadRequest):
    """
    SSE endpoint streaming SteamCMD output.
    Event types: "log", "done", "error", "steam_guard"
    """
    if not find_steamcmd():
        async def no_steamcmd():
            yield f"data: {json.dumps({'type': 'error', 'line': get_install_instructions()})}\n\n"
        return StreamingResponse(no_steamcmd(), media_type="text/event-stream")

    async def event_generator():
        async for line in stream_download(
            req.app_id,
            req.workshop_ids,
            req.output_dir,
            username=req.username,
        ):
            if line.startswith("SUCCESS:"):
                yield f"data: {json.dumps({'type': 'done', 'path': line[8:]})}\n\n"
            elif line.startswith("ERROR:"):
                yield f"data: {json.dumps({'type': 'error', 'line': line[6:]})}\n\n"
            elif line == "STEAMGUARD:":
                yield f"data: {json.dumps({'type': 'steam_guard'})}\n\n"
            elif line == "NEED_PASSWORD:":
                yield f"data: {json.dumps({'type': 'need_password'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'log', 'line': line})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/download/input")
async def download_input(body: SteamGuardInput):
    """Submit Steam Guard / 2FA code to the active SteamCMD process."""
    await send_steamcmd_input(body.code.strip())
    return {"ok": True}


@app.get("/api/status")
async def status():
    return {
        "steamcmd": find_steamcmd() or None,
        "has_api_key": bool(get_api_key()),
    }
