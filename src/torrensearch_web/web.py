"""
torrensearch web UI — simple Flask app protected by Basic Auth.

Default user/user

Run:
  TORRENSEARCH_WEB_USER=admin TORRENSEARCH_WEB_PASSWORD=secret uv run torrensearch-web
"""

import base64
import functools
import hmac
import os
import sys
from typing import Any

from flask import Flask, Response, render_template, request
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from torrensearch import CATEGORIES, init_config, list_engines, search

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=[])

_CACHE_TTL = int(os.environ.get("torrensearch_CACHE_TTL", 300))
cache = Cache(
    app, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": _CACHE_TTL}
)

_USER = os.environ.get("TORRENSEARCH_WEB_USER", "user")
_PASS = os.environ.get("TORRENSEARCH_WEB_PASSWORD", "user")


def _require_auth(f):  # type: ignore[no-untyped-def]
    @functools.wraps(f)
    @limiter.limit("20 per minute")
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                user, _, password = base64.b64decode(auth[6:]).decode().partition(":")
                if hmac.compare_digest(user, _USER) and hmac.compare_digest(
                    password, _PASS
                ):
                    return f(*args, **kwargs)
            except Exception:
                pass
        return Response(
            "Unauthorized",
            401,
            {"WWW-Authenticate": 'Basic realm="torrensearch"'},
        )

    return wrapper



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


@app.get("/")
@_require_auth
def index() -> str:
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat", "all")
    engines_raw = request.args.get("engines", "").strip()
    limit = request.args.get("limit", 40, type=int) or 40

    results = None
    errors: list[str] = []

    if q:
        engines = [e.strip() for e in engines_raw.split(",") if e.strip()] or None
        if cat not in CATEGORIES:
            cat = "all"
        cache_key = f"{q}|{engines_raw}|{cat}"
        cached = cache.get(cache_key)
        if cached is not None:
            raw_results, errors = cached
        else:
            raw_results, errors = search(q, engines, cat)
            cache.set(cache_key, (raw_results, errors))
        results = []
        for r in raw_results[:limit]:
            r["size_fmt"] = _fmt_size(r.get("size"))
            r["seeds_fmt"] = _fmt_num(r.get("seeds", -1))
            r["leech_fmt"] = _fmt_num(r.get("leech", -1))
            r["seed_class"] = _seed_class(r.get("seeds", -1))
            r.setdefault("desc_link", "")
            results.append(r)

    return render_template(
        "index.html",
        q=q,
        cat=cat,
        categories=sorted(CATEGORIES),
        engines_raw=engines_raw,
        limit=limit,
        results=results,
        errors=errors,
    )


def main() -> None:
    init_config()

    if not _PASS:
        print(
            "error: TORRENSEARCH_WEB_PASSWORD is not set — refusing to start without a password",
            file=sys.stderr,
        )
        sys.exit(1)

    host = os.environ.get("TORRENSEARCH_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("TORRENSEARCH_WEB_PORT", 5000))
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
