"""
torrensearch web UI — FastAPI app protected by Basic Auth.

Default user/user

Run:
  TORRENSEARCH_WEB_USER=admin TORRENSEARCH_WEB_PASSWORD=secret uv run torrensearch-web
"""

import dataclasses
import hmac
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from torrensearch import CATEGORIES, init_config, search

_USER = os.environ.get("TORRENSEARCH_WEB_USER", "user")
_PASS = os.environ.get("TORRENSEARCH_WEB_PASSWORD", "user")
_CACHE_TTL = int(os.environ.get("TORRENSEARCH_CACHE_TTL", 300))

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(_: FastAPI):
    FastAPICache.init(InMemoryBackend(), prefix="torrensearch")
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

security = HTTPBasic()


@cache(expire=_CACHE_TTL)
async def _cached_search(q: str, engines_raw: str, cat: str) -> tuple[list[dict], list[str]]:
    engine_list = [e.strip() for e in engines_raw.split(",") if e.strip()] or None
    raw_results, errors = await search(q, engine_list, cat)
    return [dataclasses.asdict(r) for r in raw_results], errors


def _check_auth(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> HTTPBasicCredentials:
    ok = hmac.compare_digest(credentials.username, _USER) and hmac.compare_digest(
        credentials.password, _PASS
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="torrensearch"'},
        )
    return credentials


def _fmt_size(raw: Any) -> str:
    s = str(raw).strip()
    if s in ("-1", "", "None"):
        return "?"
    if s.endswith(" B"):
        try:
            b = float(s[:-2].strip())
            for unit in ("B", "KB", "MB", "GB", "TB"):
                if b < 1024:
                    return f"{b:.1f} {unit}"
                b /= 1024
        except ValueError:
            pass
    return s


def _seed_class(raw: Any) -> str:
    try:
        n = int(raw)
    except (ValueError, TypeError):
        return "seeds-none"
    if n >= 100:
        return "seeds-high"
    if n >= 10:
        return "seeds-mid"
    if n >= 0:
        return "seeds-low"
    return "seeds-none"


def _fmt_num(raw: Any) -> str:
    try:
        n = int(raw)
        return "?" if n < 0 else str(n)
    except (ValueError, TypeError):
        return "?"


@app.get("/", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def index(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(_check_auth)],
    q: str = "",
    cat: str = "all",
    engines: str = "",
    limit: int = 40,
) -> HTMLResponse:
    q = q.strip()
    engines_raw = engines.strip()
    limit = limit or 40

    results = None
    errors: list[str] = []

    if q:
        if cat not in CATEGORIES:
            cat = "all"
        raw_results, errors = await _cached_search(q, engines_raw, cat)
        results = []
        for r in raw_results[:limit]:
            r["size_fmt"] = _fmt_size(r.get("size"))
            r["seeds_fmt"] = _fmt_num(r.get("seeds", -1))
            r["leech_fmt"] = _fmt_num(r.get("leech", -1))
            r["seed_class"] = _seed_class(r.get("seeds", -1))
            results.append(r)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "q": q,
            "cat": cat,
            "categories": sorted(CATEGORIES),
            "engines_raw": engines_raw,
            "limit": limit,
            "results": results,
            "errors": errors,
        },
    )


def main() -> None:
    init_config()

    if not _PASS:
        print(
            "error: TORRENSEARCH_WEB_PASSWORD is not set "
            "— refusing to start without a password",
            file=sys.stderr,
        )
        sys.exit(1)

    host = os.environ.get("TORRENSEARCH_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("TORRENSEARCH_WEB_PORT", 8000))
    uvicorn.run(
        "torrensearch_web.web:app",
        host=host,
        port=port,
        workers=os.cpu_count(),
    )


if __name__ == "__main__":
    main()
