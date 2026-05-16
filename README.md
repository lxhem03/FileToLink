# 🎬 FileToLink — Advanced Telegram File Streamer Bot

A powerful Telegram bot that generates **stream** and **download** links for files uploaded to it. Built with Pyrogram and aiohttp, featuring a fully custom browser-based video player with subtitle support, multi-audio track switching, and external player integration.

---

## ✨ Features

### Bot Features
- 📥 **Instant link generation** — upload any file, get a stream link and download link immediately
- ⚠️ **Filename validation** — rejects files with no filename and prompts user to rename
- 👥 **Multi-client support** — multiple Telegram bot clients load-balanced for concurrent users
- 🗄️ **MongoDB integration** — user tracking and session management
- 🔗 **Shortlink support** — optional URL shortening via Shortzy
- 📊 **200 Pyrogram workers** — handles high concurrency without blocking

### Streaming Page
- 🎥 **Custom HTML5 video player** — fully custom control bar (no native browser controls)
  - ⏪ Rewind 10s / ⏩ Forward 10s buttons
  - 🔊 Volume slider + mute toggle
  - ⏱️ Progress bar with scrubbing support
  - ⛶ Fullscreen (fullscreens the entire player wrapper, keeping all controls visible)
  - ⚙️ Settings gear button (visible in both normal and fullscreen mode)
  - ⌨️ Keyboard shortcuts: `Space` play/pause, `←/→` ±10s, `↑/↓` volume, `M` mute, `F` fullscreen
  - 👆 Double-tap left/right to skip 10s on mobile

### Settings Panel (⚙️)
- 🔊 **Audio track selector** — switch between multiple audio tracks (e.g. Japanese/English dubs)
- 💬 **Subtitle selector** — switch between multiple subtitle tracks
- 🎨 **Subtitle colour** — 8 colour swatches (White, Yellow, Cyan, Green, Orange, Pink, Red, Light Blue)
- 🌑 **Subtitle background** — toggle semi-transparent black background on/off
- 🔤 **Subtitle size** — slider from 60% to 200%
- ⚡ **Playback speed** — 0.25× to 2×
- 📜 **Scrollable panel** — all settings accessible by scrolling on small screens

### Subtitle Support
- ✅ **ASS/SSA subtitles** — extracted via ffmpeg and served as WebVTT; SubOctopus WASM attempted in background for rich styling
- ✅ **SRT subtitles** — converted server-side to strict WebVTT (Python converter guarantees Chrome-compatible format)
- ✅ **Multiple subtitle tracks** — all tracks listed and switchable
- ✅ **Correct UTF-8 encoding** — handles BOM, Windows line endings, and special characters
- ✅ **In-memory caching** — subtitle tracks cached after first extraction for instant repeat access

### Audio Track Switching
- 🔄 Switches audio tracks by reloading the stream via the `/audio/` endpoint
- ⚡ Server uses `ffmpeg -c copy` (stream copy) — **no re-encoding**, preserves original audio codec and sync
- 🗂️ MKV container output — supports all audio codecs (AC3, DTS, AAC, FLAC, Opus, etc.) without conversion
- ⏩ Input-seek (`-ss` before `-i`) for fast seeking to the right position
- 🔁 Seeking after audio switch handled via debounced reload with new `?start=` timestamp

### External Player Integration
- **Android:** `intent://` deep links for MX Player, VLC, PLAYit, KM Player, nPlayer
- **iOS:** Custom URL schemes for VLC (`vlc-x-callback://`) and nPlayer
- **Desktop:** Direct `vlc://` link + clipboard copy fallback

---

## 🚀 Deployment

### Requirements
```
pyrogram==2.0.80
TgCrypto
aiohttp
python-dotenv<=0.20.0
motor
aiofiles
dnspython
apscheduler
requests
psutil
shortzy
jinja2
humanize
pytz
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `API_ID` | ✅ | Telegram API ID from my.telegram.org |
| `API_HASH` | ✅ | Telegram API Hash |
| `BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `SESSION` | ✅ | Pyrogram session string |
| `URL` | ✅ | Public URL of your deployment (e.g. `https://yourapp.koyeb.app/`) |
| `LOG_CHANNEL` | ✅ | Telegram channel ID for logging |
| `DATABASE_URI` | ✅ | MongoDB connection URI |
| `DATABASE_NAME` | ❌ | MongoDB database name (default: `FileXstreamerobot`) |
| `ADMINS` | ❌ | Space-separated Telegram user IDs |
| `PORT` | ❌ | Server port (default: `8080`) |
| `SHORTLINK` | ❌ | `True` to enable URL shortening |
| `SHORTLINK_URL` | ❌ | Shortlink provider URL |
| `SHORTLINK_API` | ❌ | Shortlink provider API key |
| `SLEEP_THRESHOLD` | ❌ | Pyrogram sleep threshold in seconds (default: `60`) |
| `PING_INTERVAL` | ❌ | Keep-alive ping interval in seconds (default: `1200`) |

### Docker / Koyeb / Heroku

**Dockerfile** (ffmpeg required for subtitle extraction and audio track switching):
```dockerfile
FROM python:3.10.8-slim

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y git ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip3 install -U pip && pip3 install -U -r /requirements.txt

RUN mkdir /FileToLink
WORKDIR /FileToLink
COPY . /FileToLink

CMD ["python", "bot.py"]
```

---

## 🔌 API Endpoints

| Endpoint | Description |
|---|---|
| `GET /{id}/{filename}?hash=` | Download/stream the original file (Range-request seekable) |
| `GET /watch/{id}/{filename}?hash=` | Serves the streaming HTML page |
| `GET /info/{id}?hash=` | Returns JSON with audio and subtitle track list (via ffprobe) |
| `GET /audio/{id}/{track}?hash=&start=` | Streams the file remuxed with selected audio track (ffmpeg stream copy, MKV) |
| `GET /sub/{id}/{track}?hash=` | Returns subtitle track as WebVTT (ffmpeg extraction + Python converter) |

---

## 📝 Changes & Improvements (vs Original)

### `plugins/start.py`
- Added **filename validation** — rejects files without a filename with a clear error message

### `plugins/route.py`
- Added `/info/` endpoint — ffprobe-based audio and subtitle track detection
- Added `/audio/` endpoint — ffmpeg stream-copy remux for audio track switching
  - Uses MKV container (`-f matroska`) — no audio re-encoding
  - Supports `?start=N` for seeking (input seek via `-ss` before `-i`)
  - `-cluster_size_limit 2M` for faster stream start
- Added `/sub/` endpoint — subtitle extraction and conversion
  - Extracts as SRT via ffmpeg then converts to WebVTT in Python
  - Python converter guarantees: correct `WEBVTT` header, `.` not `,` in timestamps, UTF-8, stripped ASS tags
  - In-memory cache (`_sub_cache`) so repeat requests are instant
  - `X-Subtitle-Format` header tells client whether source was ASS or SRT
- `Content-Disposition: attachment` on download endpoint — browser downloads directly instead of playing
- Increased Pyrogram `workers` to 200 for better concurrency

### `TechVJ/template/req.html`
- Complete rewrite of the streaming page — custom video player replacing native browser controls
- Settings panel (⚙️) inside the player wrapper — visible in fullscreen
- Audio track switching with server-side remux
- Subtitle rendering with native `<track>` element + SubOctopus WASM fallback for ASS
- Subtitle appearance customisation (colour, background, size)
- Playback speed control
- External player buttons with correct `intent://` deep links for Android
- Double-tap skip on mobile, keyboard shortcuts

### `TechVJ/bot/__init__.py`
- Increased `workers` from 50 to 200

---

## 🛠️ Tech Stack

- **Bot framework:** Pyrogram (pyrofork) + TgCrypto
- **Web server:** aiohttp
- **Database:** MongoDB (Motor async driver)
- **Media processing:** ffmpeg + ffprobe
- **Subtitle rendering:** Native WebVTT `<track>` + JavascriptSubtitlesOctopus (WASM)
- **Frontend:** Vanilla JS + CSS (no frameworks)

---

## 📄 Credits

bot by [Telegram Guy](https://t.me/The_TGguy) / [Nectar](https://t.me/TGXNectar).  
Enhanced streaming page and multi-track support added on top of the original.

> ⚠️ **Note:** ffmpeg and ffprobe must be installed on the server for subtitle extraction and audio track switching to work. Add `ffmpeg` to your Dockerfile or server setup.
