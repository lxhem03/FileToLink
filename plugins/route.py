# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, math, logging, secrets, mimetypes, time, asyncio, subprocess, os, tempfile
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

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("BenFilterBot")

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


# ── Subtitle extraction endpoint ──────────────────────────────────────────────
# GET /sub/{msg_id}/{track_index}?hash=XXXX
# Streams a single subtitle track as WebVTT, extracted on-the-fly with ffmpeg.
# This is the ONLY reliable way to expose MKV-embedded subtitles to browsers.
@routes.get(r"/sub/{id:\d+}/{track:\d+}", allow_head=True)
async def subtitle_handler(request: web.Request):
    try:
        id          = int(request.match_info["id"])
        track_index = int(request.match_info["track"])
        secure_hash = request.rel_url.query.get("hash", "")

        # Validate hash
        index = min(work_loads, key=work_loads.get)
        faster_client = multi_clients[index]
        if faster_client not in class_cache:
            class_cache[faster_client] = ByteStreamer(faster_client)
        tg_connect = class_cache[faster_client]
        file_id = await tg_connect.get_file_properties(id)

        if file_id.unique_id[:6] != secure_hash:
            raise web.HTTPForbidden(text="Invalid hash")

        # Build the stream URL for this file (same URL the player uses)
        from urllib.parse import quote_plus
        file_url = f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"

        # ffmpeg: read from HTTP, extract subtitle track track_index as WebVTT
        cmd = [
            "ffmpeg", "-v", "quiet",
            "-i", file_url,
            "-map", f"0:s:{track_index}",
            "-f", "webvtt",
            "pipe:1"
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode != 0 or not stdout:
            logging.warning(f"ffmpeg subtitle extract failed for id={id} track={track_index}: {stderr.decode()[:200]}")
            raise web.HTTPNotFound(text="Subtitle track not found or ffmpeg not available")

        return web.Response(
            body=stdout,
            content_type="text/vtt",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            }
        )
    except (web.HTTPForbidden, web.HTTPNotFound):
        raise
    except asyncio.TimeoutError:
        raise web.HTTPGatewayTimeout(text="Subtitle extraction timed out")
    except Exception as e:
        logging.error(f"Subtitle handler error: {e}")
        raise web.HTTPInternalServerError(text=str(e))


# ── Media info endpoint ───────────────────────────────────────────────────────
# GET /info/{msg_id}?hash=XXXX
# Returns JSON with audio track list and subtitle track list, probed via ffprobe.
# The watch page fetches this on load to populate the track selectors.
@routes.get(r"/info/{id:\d+}", allow_head=True)
async def info_handler(request: web.Request):
    import json
    try:
        id          = int(request.match_info["id"])
        secure_hash = request.rel_url.query.get("hash", "")

        index = min(work_loads, key=work_loads.get)
        faster_client = multi_clients[index]
        if faster_client not in class_cache:
            class_cache[faster_client] = ByteStreamer(faster_client)
        tg_connect = class_cache[faster_client]
        file_id = await tg_connect.get_file_properties(id)

        if file_id.unique_id[:6] != secure_hash:
            raise web.HTTPForbidden(text="Invalid hash")

        from urllib.parse import quote_plus
        file_url = f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"

        # ffprobe: extract stream metadata as JSON
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            file_url
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            return web.json_response({"audio": [], "subtitles": [], "error": "probe timeout"})

        audio_tracks = []
        subtitle_tracks = []

        if stdout:
            try:
                probe = json.loads(stdout)
                audio_idx = 0
                sub_idx   = 0
                for stream in probe.get("streams", []):
                    codec_type = stream.get("codec_type", "")
                    tags = stream.get("tags", {})
                    lang  = tags.get("language", tags.get("LANGUAGE", ""))
                    title = tags.get("title",    tags.get("TITLE", ""))
                    label = title or lang or ""

                    if codec_type == "audio":
                        audio_tracks.append({
                            "index": audio_idx,
                            "label": label or f"Audio {audio_idx + 1}",
                            "lang":  lang,
                        })
                        audio_idx += 1
                    elif codec_type == "subtitle":
                        codec = stream.get("codec_name", "")
                        # Only expose subtitle codecs ffmpeg can convert to WebVTT
                        if codec in ("subrip", "srt", "ass", "ssa", "webvtt", "mov_text", "hdmv_pgs_subtitle"):
                            subtitle_tracks.append({
                                "index": sub_idx,
                                "label": label or f"Subtitle {sub_idx + 1}",
                                "lang":  lang,
                                "codec": codec,
                            })
                        sub_idx += 1
            except Exception as parse_err:
                logging.warning(f"ffprobe parse error: {parse_err}")

        return web.json_response(
            {"audio": audio_tracks, "subtitles": subtitle_tracks},
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except web.HTTPForbidden:
        raise
    except Exception as e:
        logging.error(f"Info handler error: {e}")
        return web.json_response({"audio": [], "subtitles": [], "error": str(e)})


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

class_cache = {}

_cache_locks: dict = {}

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)

    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client not in class_cache:
        class_cache[faster_client] = ByteStreamer(faster_client)
        logging.debug(f"Created new ByteStreamer for client {index}")
    tg_connect = class_cache[faster_client]

    if id not in tg_connect.cached_file_ids:
        if id not in _cache_locks:
            _cache_locks[id] = asyncio.Lock()
        async with _cache_locks[id]:
            if id not in tg_connect.cached_file_ids:
                await tg_connect.generate_file_properties(id)

    file_id = tg_connect.cached_file_ids[id]

    if file_id.unique_id[:6] != secure_hash:
        logging.debug(f"Invalid hash for message with ID {id}")
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
        disposition = "inline"

        if mime_type:
            if not file_name:
                try:
                    file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
                except (IndexError, AttributeError):
                    file_name = f"{secrets.token_hex(2)}.unknown"
        else:
            if file_name:
                mime_type = mimetypes.guess_type(file_id.file_name)[0] or "application/octet-stream"
            else:
                mime_type = "application/octet-stream"
                file_name = f"{secrets.token_hex(2)}.unknown"

        if mime_type and mime_type.split("/")[0] in ("video", "audio"):
            disposition = "inline"
        else:
            disposition = "attachment"

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
