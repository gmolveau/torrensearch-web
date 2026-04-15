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

from flask import Flask, Response, render_template_string, request
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


_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>torrensearch</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: ui-monospace, monospace; background: #0f1117; color: #e2e8f0; min-height: 100vh; padding: 2rem 1rem; }
  a { color: inherit; text-decoration: none; }

  header { max-width: 900px; margin: 0 auto 2rem; display: flex; align-items: baseline; gap: 1rem; }
  header h1 { font-size: 1.4rem; color: #7dd3fc; letter-spacing: .05em; }
  header span { font-size: .8rem; color: #64748b; }

  form { max-width: 900px; margin: 0 auto 2rem; display: flex; flex-wrap: wrap; gap: .5rem; }
  input, select { background: #1e2433; border: 1px solid #334155; color: #e2e8f0; border-radius: 6px; padding: .45rem .75rem; font: inherit; font-size: .9rem; }
  input[name=q] { flex: 1 1 260px; }
  button { background: #0ea5e9; border: none; color: #fff; border-radius: 6px; padding: .45rem 1.25rem; font: inherit; font-size: .9rem; cursor: pointer; }
  button:hover { background: #38bdf8; }

  .meta { max-width: 900px; margin: 0 auto 1rem; font-size: .8rem; color: #64748b; }

  table { width: 100%; max-width: 900px; margin: 0 auto; border-collapse: collapse; font-size: .85rem; }
  th { text-align: left; padding: .4rem .6rem; color: #7dd3fc; border-bottom: 1px solid #334155; white-space: nowrap; }
  td { padding: .45rem .6rem; border-bottom: 1px solid #1e2433; vertical-align: top; }
  tr:hover td { background: #1e2433; cursor: pointer; }
  .seeds-high { color: #4ade80; font-weight: 600; }
  .seeds-mid  { color: #facc15; }
  .seeds-low  { color: #f87171; }
  .seeds-none { color: #475569; }

  /* magnet panel */
  .magnet-row td { background: #1a2236 !important; padding: .6rem 1rem; }
  .magnet-box { display: flex; gap: .5rem; align-items: flex-start; flex-wrap: wrap; }
  .magnet-link { flex: 1; word-break: break-all; font-size: .78rem; color: #94a3b8; }
  .copy-btn { background: #334155; border: none; color: #e2e8f0; border-radius: 4px; padding: .25rem .6rem; font: inherit; font-size: .78rem; cursor: pointer; white-space: nowrap; }
  .copy-btn:hover { background: #475569; }
  .copied { color: #4ade80 !important; }

  .errors { max-width: 900px; margin: 0 auto 1rem; }
  .error  { color: #f87171; font-size: .8rem; margin-bottom: .25rem; }
  .empty  { max-width: 900px; margin: 2rem auto; text-align: center; color: #475569; }
</style>
</head>
<body>

<header>
  <h1>torrensearch</h1>
  <span>torrent search</span>
</header>

<form method="get" action="/">
  <input name="q" type="text" placeholder="search query…" value="{{ q }}" autofocus required>
  <select name="cat">
    {% for c in categories %}
    <option value="{{ c }}" {% if c == cat %}selected{% endif %}>{{ c }}</option>
    {% endfor %}
  </select>
  <input name="engines" type="text" placeholder="engines (default: all)" value="{{ engines_raw }}" style="flex:0 1 200px">
  <input name="limit" type="number" min="5" max="100" value="{{ limit }}" style="flex:0 1 70px" title="max results">
  <button type="submit">Search</button>
</form>

{% if errors %}
<div class="errors">
  {% for e in errors %}<div class="error">⚠ {{ e }}</div>{% endfor %}
</div>
{% endif %}

{% if results is not none %}
  {% if results %}
  <div class="meta">{{ results|length }} result(s) for "{{ q }}"</div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Name</th>
        <th>Size</th>
        <th>Seeds</th>
        <th>Leech</th>
        <th>Engine</th>
      </tr>
    </thead>
    <tbody>
    {% for r in results %}
      <tr class="result-row" data-idx="{{ loop.index }}">
        <td>{{ loop.index }}</td>
        <td>{{ r.name }}</td>
        <td>{{ r.size_fmt }}</td>
        <td class="{{ r.seed_class }}">{{ r.seeds_fmt }}</td>
        <td>{{ r.leech_fmt }}</td>
        <td>{{ r._engine }}</td>
      </tr>
      <tr class="magnet-row" id="magnet-{{ loop.index }}" style="display:none">
        <td colspan="6">
          <div class="magnet-box">
            <span class="magnet-link">{{ r.link }}</span>
            <button class="copy-btn" data-link="{{ r.link }}">Copy</button>
            {% if r.desc_link and r.desc_link != '-1' %}
            <a href="{{ r.desc_link }}" target="_blank" rel="noopener">
              <button class="copy-btn" type="button">Info page ↗</button>
            </a>
            {% endif %}
          </div>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty">No results found for "{{ q }}".</div>
  {% endif %}
{% endif %}

<script>
document.querySelectorAll('.result-row').forEach(row => {
  row.addEventListener('click', () => {
    const panel = document.getElementById('magnet-' + row.dataset.idx);
    const visible = panel.style.display !== 'none';
    document.querySelectorAll('.magnet-row').forEach(r => r.style.display = 'none');
    if (!visible) panel.style.display = 'table-row';
  });
});

document.querySelectorAll('.copy-btn[data-link]').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(btn.dataset.link).then(() => {
      btn.textContent = 'Copied!';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
    });
  });
});
</script>
</body>
</html>
"""


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

    return render_template_string(
        _HTML,
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
