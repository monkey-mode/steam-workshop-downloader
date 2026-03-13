# Steam Workshop Downloader

Browse and download Steam Workshop mods via a web UI or CLI.

```
steam-workshop-downloader/
├── backend/    Python API server + CLI (FastAPI + Click)
└── frontend/   Web UI (Next.js)
```

## Requirements

- Python 3.10+
- Node.js 18+
- [SteamCMD](https://developer.valvesoftware.com/wiki/SteamCMD) — required for downloading mods

### Install SteamCMD (macOS)

```bash
brew install steamcmd
# runs as steamcmd.sh
```

### Install SteamCMD (Linux)

```bash
# Ubuntu/Debian
sudo apt install steamcmd
```

---

## Backend

### Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run the API server

```bash
cd backend
python serve.py
# Server starts at http://localhost:8000
```

### Optional: Steam API key

Set `STEAM_API_KEY` to enable the full `IPublishedFileService` browse API (richer metadata, no scraping):

```bash
export STEAM_API_KEY=your_key_here
python serve.py
```

Get a free key at https://steamcommunity.com/dev/apikey

---

## Frontend

### Setup & run

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

### Build for production

```bash
npm run build
npm start
```

---

## Web UI Usage

1. Start the backend (`python serve.py`) and frontend (`npm run dev`)
2. Enter an **App ID** or paste a Steam Workshop URL in the header (default: `255710` = Cities: Skylines)
3. Browse mods — click cards to select them
4. Set **output folder** and **Steam username** in the download bar at the bottom
5. Click **Download** — live SteamCMD output streams in the terminal panel

> **Note:** Most paid-game mods require your Steam username. Enter it in the username field (SteamCMD will prompt for your password in the terminal where `python serve.py` is running). Free-to-play game mods work with `anonymous`.

---

## CLI Usage

```bash
cd backend
source .venv/bin/activate
```

### Browse workshop

```bash
swdl browse 255710
swdl browse 255710 --sort new --count 10
swdl browse 255710 --search "road"
swdl browse "https://steamcommunity.com/app/255710/workshop/"
```

Sort options: `trend` (default), `top`, `new`, `favorites`

### Get item info

```bash
swdl info 123456789
swdl info "https://steamcommunity.com/sharedfiles/filedetails/?id=123456789"
```

### Download mods

```bash
# Single mod (anonymous login, for F2P games)
swdl download 123456789 -a 255710

# Multiple mods
swdl download 123456789 987654321 -a 255710

# With your Steam account (required for paid games)
swdl download 123456789 -a 255710 -u your_steam_username

# Custom output directory
swdl download 123456789 -a 255710 -o ~/mods
```

Downloaded files are placed at:
```
<output_dir>/steamapps/workshop/content/<app_id>/<workshop_id>/
```

### Check SteamCMD

```bash
swdl check
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/browse` | Browse workshop items |
| `GET` | `/api/item/{id}` | Get single item details |
| `POST` | `/api/download/stream` | Stream download via SSE |
| `GET` | `/api/status` | Check SteamCMD + API key status |

### Browse params

| Param | Default | Description |
|-------|---------|-------------|
| `app_id` | required | Steam App ID |
| `sort` | `trend` | `trend`, `top`, `new`, `favorites` |
| `page` | `1` | Page number |
| `count` | `20` | Items per page (max 50) |
| `search` | `""` | Search query |
