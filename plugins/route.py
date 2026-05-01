# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, math, logging, secrets, mimetypes, time, asyncio, json as _json
from info import *
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from TechVJ.bot import multi_clients, work_loads, TechVJBot
from TechVJ.server.exceptions import FIleNotFound, InvalidHash
from TechVJ import StartTime, __version__
from TechVJ.util.custom_dl import ByteStreamer
from TechVJ.util.time_format import get_readable_time
from TechVJ.util.render_template import render_page

routes = web.RouteTableDef()

# ── Shared ByteStreamer cache ──────────────────────────────────────────────────
class_cache = {}
_cache_locks: dict = {}

async def _get_streamer_and_file(id: int, secure_hash: str):
    """Resolve ByteStreamer + validate hash. Returns (tg_connect, file_id, index)."""
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    if faster_client not in class_cache:
        class_cache[faster_client] = ByteStreamer(faster_client)
    tg_connect = class_cache[faster_client]
    file_id = await tg_connect.get_file_properties(id)
    if file_id.unique_id[:6] != secure_hash:
        raise InvalidHash
    return tg_connect, file_id, index, faster_client

# ── Root ──────────────────────────────────────────────────────────────────────
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("BenFilterBot")

# ── Watch page ────────────────────────────────────────────────────────────────
@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def watch_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return web.Response(text=await render_page(id, secure_hash), content_type='text/html')
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

# ── /info/{id}?hash= ─────────────────────────────────────────────────────────
# Returns JSON: { audio: [{index, label, lang}], subtitles: [{index, label, lang, codec}] }
# Probed via ffprobe reading the first few MB of the stream.
@routes.get(r"/info/{id:\d+}", allow_head=True)
async def info_handler(request: web.Request):
    try:
        id          = int(request.match_info["id"])
        secure_hash = request.rel_url.query.get("hash", "")

        _, file_id, _, _ = await _get_streamer_and_file(id, secure_hash)

        from urllib.parse import quote_plus
        file_url = f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"

        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            file_url
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            return web.json_response({"audio": [], "subtitles": [], "error": "probe timeout"},
                                     headers={"Access-Control-Allow-Origin": "*"})

        audio_tracks, subtitle_tracks = [], []
        if stdout:
            try:
                probe   = _json.loads(stdout)
                aidx = sidx = 0
                for stream in probe.get("streams", []):
                    ctype = stream.get("codec_type", "")
                    tags  = stream.get("tags", {})
                    lang  = tags.get("language", tags.get("LANGUAGE", ""))
                    title = tags.get("title",    tags.get("TITLE", ""))
                    if ctype == "audio":
                        audio_tracks.append({
                            "index": aidx,
                            "label": title or f"Audio {aidx + 1}",
                            "lang":  lang,
                        })
                        aidx += 1
                    elif ctype == "subtitle":
                        codec = stream.get("codec_name", "")
                        if codec in ("subrip","srt","ass","ssa","webvtt","mov_text","hdmv_pgs_subtitle"):
                            subtitle_tracks.append({
                                "index": sidx,
                                "label": title or f"Subtitle {sidx + 1}",
                                "lang":  lang,
                                "codec": codec,
                            })
                        sidx += 1
            except Exception as e:
                logging.warning(f"ffprobe parse error: {e}")

        return web.json_response(
            {"audio": audio_tracks, "subtitles": subtitle_tracks},
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except InvalidHash:
        raise web.HTTPForbidden(text="Invalid hash")
    except Exception as e:
        logging.error(f"Info handler error: {e}")
        return web.json_response({"audio": [], "subtitles": [], "error": str(e)},
                                 headers={"Access-Control-Allow-Origin": "*"})

# ── /audio/{id}/{track}?hash= ─────────────────────────────────────────────────
# Streams the file remuxed to only the selected audio track (stream copy, low CPU).
# The watch page swaps vid.src to this URL when the user picks a different track.
# Range requests are NOT supported here — this is for streaming only.
@routes.get(r"/audio/{id:\d+}/{track:\d+}", allow_head=True)
async def audio_handler(request: web.Request):
    try:
        id          = int(request.match_info["id"])
        track_index = int(request.match_info["track"])
        secure_hash = request.rel_url.query.get("hash", "")

        _, file_id, _, _ = await _get_streamer_and_file(id, secure_hash)

        from urllib.parse import quote_plus
        file_url = f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"

        # -map 0:v:0  → first video stream
        # -map 0:a:{n} → nth audio stream
        # -c copy      → no transcode, just remux — very low CPU
        # -f matroska  → output as MKV so browser gets a proper container
        cmd = [
            "ffmpeg", "-v", "quiet",
            "-i", file_url,
            "-map", "0:v:0",
            "-map", f"0:a:{track_index}",
            "-c", "copy",
            "-f", "matroska",
            "pipe:1"
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Stream ffmpeg output directly to the browser
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "video/x-matroska",
                "Content-Disposition": f'inline; filename="{file_id.file_name}"',
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
            }
        )
        await response.prepare(request)

        try:
            while True:
                chunk = await proc.stdout.read(1024 * 256)  # 256 KB chunks
                if not chunk:
                    break
                await response.write(chunk)
        finally:
            proc.kill()
            await proc.wait()

        await response.write_eof()
        return response

    except InvalidHash:
        raise web.HTTPForbidden(text="Invalid hash")
    except ConnectionResetError:
        pass
    except Exception as e:
        logging.error(f"Audio handler error: {e}")
        raise web.HTTPInternalServerError(text=str(e))

# ── /sub/{id}/{track}?hash= ───────────────────────────────────────────────────
# Extracts a subtitle track as WebVTT using ffmpeg.
# Results are cached in memory so repeated requests (e.g. after audio switch)
# are instant and don't re-run ffmpeg.
_sub_cache: dict = {}  # key: (id, track_index) → bytes

@routes.get(r"/sub/{id:\d+}/{track:\d+}", allow_head=True)
async def subtitle_handler(request: web.Request):
    try:
        id          = int(request.match_info["id"])
        track_index = int(request.match_info["track"])
        secure_hash = request.rel_url.query.get("hash", "")

        _, file_id, _, _ = await _get_streamer_and_file(id, secure_hash)

        cache_key = (id, track_index)
        if cache_key in _sub_cache:
            logging.debug(f"Subtitle cache hit for id={id} track={track_index}")
            return web.Response(
                body=_sub_cache[cache_key],
                content_type="text/vtt",
                headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=86400"}
            )

        from urllib.parse import quote_plus
        file_url = f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"

        # -nostdin          : prevent ffmpeg hanging waiting for input
        # -probesize 50M    : read up to 50MB to find streams (MKV index is at end)
        # -analyzeduration 0: don't waste time analysing audio/video duration
        # -map 0:s:{n}      : select nth subtitle stream only
        # -f webvtt         : output as WebVTT (browser-native format)
        # stderr to PIPE so we can log errors; not quiet so errors are visible
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-probesize", "50M",
            "-analyzeduration", "0",
            "-i", file_url,
            "-map", f"0:s:{track_index}",
            "-f", "webvtt",
            "pipe:1"
        ]
        logging.info(f"Running ffmpeg subtitle extraction: id={id} track={track_index}")
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logging.error(f"ffmpeg subtitle timeout: id={id} track={track_index}")
            raise web.HTTPGatewayTimeout(text="Subtitle extraction timed out — file may be too large")

        if proc.returncode != 0 or not stdout:
            err_msg = stderr.decode(errors="replace")[:500]
            logging.warning(f"ffmpeg sub failed id={id} track={track_index} rc={proc.returncode}: {err_msg}")
            raise web.HTTPNotFound(text=f"Subtitle track not found. ffmpeg error: {err_msg[:200]}")

        # Cache in memory (subtitles are typically 100KB–2MB)
        _sub_cache[cache_key] = stdout
        logging.info(f"Subtitle extracted and cached: id={id} track={track_index} size={len(stdout)}B")

        return web.Response(
            body=stdout,
            content_type="text/vtt",
            headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=86400"}
        )
    except (web.HTTPForbidden, web.HTTPNotFound, web.HTTPGatewayTimeout):
        raise
    except InvalidHash:
        raise web.HTTPForbidden(text="Invalid hash")
    except Exception as e:
        logging.error(f"Subtitle handler error: {e}", exc_info=True)
        raise web.HTTPInternalServerError(text=str(e))

# ── Download / stream ─────────────────────────────────────────────────────────
@routes.get(r"/{path:\S+}", allow_head=True)
async def download_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return await media_streamer(request, id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")
    if faster_client not in class_cache:
        class_cache[faster_client] = ByteStreamer(faster_client)
    tg_connect = class_cache[faster_client]
    if id not in tg_connect.cached_file_ids:
        if id not in _cache_locks:
            _cache_locks[id] = asyncio.Lock()
        async with _cache_locks[id]:
            if id not in tg_connect.cached_file_ids:
                await tg_connect.generate_file_properties(id)
    file_id = tg_connect.cached_file_ids[id]
    if file_id.unique_id[:6] != secure_hash:
        raise InvalidHash
    file_size = file_id.file_size
    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1
    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )
    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)
    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1
    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    work_loads[index] += 1
    try:
        body = tg_connect.yield_file(
            file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
        )
        mime_type = file_id.mime_type
        file_name = file_id.file_name
        if mime_type:
            if not file_name:
                try:
                    file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
                except:
                    file_name = f"{secrets.token_hex(2)}.unknown"
        else:
            if file_name:
                mime_type = mimetypes.guess_type(file_id.file_name)[0] or "application/octet-stream"
            else:
                mime_type = "application/octet-stream"
                file_name = f"{secrets.token_hex(2)}.unknown"
        disposition = "inline" if mime_type and mime_type.split("/")[0] in ("video","audio") else "attachment"
        return web.Response(
            status=206 if range_header else 200,
            body=body,
            headers={
                "Content-Type": str(mime_type),
                "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
                "Content-Length": str(req_length),
                "Content-Disposition": f'{disposition}; filename="{file_name}"',
                "Accept-Ranges": "bytes",
            },
        )
    finally:
        work_loads[index] = max(0, work_loads[index] - 1)
