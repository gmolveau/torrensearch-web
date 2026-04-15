# torrensearch-web

> **Disclaimer:** This project is for educational purposes only. Use it only to search for content you have the legal right to access. The authors are not responsible for any misuse.

A simple web UI for `torrensearch`. Search torrents from a browser, click a result to reveal its magnet link, and copy it with one click. Protected by HTTP Basic Auth.

## Prerequisites

- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- The [`torrensearch`](https://github.com/gmolveau/torrensearch) core library

---

## 1. Run

```bash
TORRENSEARCH_WEB_USER=admin TORRENSEARCH_WEB_PASSWORD=secret uv run torrensearch-web
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. You will be prompted for the username and password you set above.

If `TORRENSEARCH_WEB_PASSWORD` is not set, the app starts without authentication and prints a warning to stderr.

---

## 2. Configuration

| Variable                    | Default     | Description         |
| --------------------------- | ----------- | ------------------- |
| `TORRENSEARCH_WEB_USER`     | `admin`     | Basic Auth username |
| `TORRENSEARCH_WEB_PASSWORD` | *(empty)*   | Basic Auth password |
| `TORRENSEARCH_WEB_HOST`     | `127.0.0.1` | Bind address        |
| `TORRENSEARCH_WEB_PORT`     | `8000`      | Bind port           |

To expose the UI on your local network:

```bash
TORRENSEARCH_WEB_HOST=0.0.0.0 TORRENSEARCH_WEB_PASSWORD=secret uv run torrensearch-web
```

---

## 3. Usage

### Search form

| Field    | Description                                                                                |
| -------- | ------------------------------------------------------------------------------------------ |
| Query    | Free-text search query                                                                     |
| Category | Filter by category (`all`, `anime`, `books`, `games`, `movies`, `music`, `software`, `tv`) |
| Engines  | Comma-separated engine names to use (leave blank for all)                                  |
| Limit    | Maximum number of results to display (5–100, default 40)                                   |

### Results table

Results are sorted by seeders (highest first). Each row shows:

- **Name** — full torrent name
- **Size** — formatted file size
- **Seeds / Leech** — seeder and leecher counts (colour-coded: green ≥ 100, yellow ≥ 10, red < 10)
- **Engine** — which engine returned the result

Click any row to expand a panel with the full magnet link. From there you can:

- **Copy** — copy the magnet link to the clipboard
- **Info page ↗** — open the engine's detail page in a new tab (when available)

---

## 4. Jackett integration

To search private or additional public trackers, configure the Jackett engine. See the [Jackett section in the core README](https://github.com/gmolveau/torrensearch/README.md#jackett) for full setup instructions.

A config file for the jacket engine can be provided to the container in the `/config` volume.

Once Jackett is running and configured, include it in searches by typing `jackett` in the **Engines** field.

---

## 5. Security notes

- Set a strong `TORRENSEARCH_WEB_PASSWORD` before exposing the app outside localhost.
- The app uses HTTP Basic Auth — use a reverse proxy with TLS (nginx, Caddy) if accessing over a network.
- Do not run as root.
