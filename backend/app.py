"""Tek-kutu OSINT API + statik frontend."""
import json
import time
import asyncio
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .variants import build_variants
from .merger import score_hit, merge_profile
from .connectors.registry import fanout, REGISTRY

app = FastAPI(title="OSINT Tek Kutu")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

AUDIT = []
BASE = Path(__file__).resolve().parent.parent

@app.get("/api/health")
def health():
    return {"ok": True, "connectors": len(REGISTRY)}

@app.get("/api/sources")
def sources():
    return {"sources": [{"name": n, "tier": t} for n, _, t in REGISTRY]}

@app.get("/api/search")
async def search_once(name: str = Query(..., min_length=2), city: str = ""):
    v = build_variants(name)
    t0 = time.time()
    raw, errors = await fanout(v, v["primary"])
    scored = [score_hit(v["primary"], dict(h), city) for h in raw]
    profile = merge_profile(v["primary"], scored)
    profile["duration_ms"] = int((time.time() - t0) * 1000)
    profile["errors"] = errors
    AUDIT.append({"q": name, "t": time.time(), "hits": len(scored)})
    return {"profile": profile, "hits": sorted(scored, key=lambda h: h.get("score", 0), reverse=True), "variants": v["all"]}

@app.get("/api/stream")
async def stream(name: str = Query(..., min_length=2), city: str = ""):
    v = build_variants(name)
    t0 = time.time()

    async def gen():
        yield f"data: {json.dumps({'type': 'job_started', 'query': v['primary'], 'variants': v['all']}, ensure_ascii=False)}\n\n"
        collected = []

        async def on_batch(tier, all_hits, errors):
            pass  # kademeler toplu akıtılıyor (basitlik için finalde)

        raw, errors = await fanout(v, v["primary"], on_batch)
        scored = [score_hit(v["primary"], dict(h), city) for h in raw]
        for h in sorted(scored, key=lambda x: x.get("score", 0), reverse=True):
            collected.append(h)
            yield f"data: {json.dumps({'type': 'candidate', **h}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
        profile = merge_profile(v["primary"], scored)
        profile["duration_ms"] = int((time.time() - t0) * 1000)
        profile["errors"] = errors
        yield f"data: {json.dumps({'type': 'merged', 'profile': profile}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'stats': {'sources_ok': len(REGISTRY) - len(errors), 'failed': len(errors), 'duration_ms': profile['duration_ms']}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

FRONT = BASE / "frontend" / "index.html"

@app.get("/")
def index():
    if FRONT.exists():
        return FileResponse(str(FRONT))
    return JSONResponse({"msg": "frontend yok", "api": "/api/search?name=Ad+Soyad"})
