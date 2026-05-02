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

# Shared cache — same as original
class_cache = {}

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("BenFilterBot")

# ── /watch/ page ──────────────────────────────────────────────────────────────
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

# ── /info/{id}?hash= — ffprobe audio/subtitle track list ─────────────────────
@routes.get(r"/info/{id:\d+}", allow_head=True)
async def info_handler(request: web.Request):
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

        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_url]
        proc = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            return web.json_response({"audio": [], "subtitles": [], "error": "probe timeout"},
                                     headers={"Access-Control-Allow-Origin": "*"})

        audio_tracks, subtitle_tracks = [], []
        if stdout:
            try:
                aidx = sidx = 0
                for stream in _json.loads(stdout).get("streams", []):
                    ctype = stream.get("codec_type", "")
                    tags  = stream.get("tags", {})
                    lang  = tags.get("language", tags.get("LANGUAGE", ""))
                    title = tags.get("title", tags.get("TITLE", ""))
                    if ctype == "audio":
                        audio_tracks.append({"index": aidx, "label": title or f"Audio {aidx+1}", "lang": lang})
                        aidx += 1
                    elif ctype == "subtitle":
                        codec = stream.get("codec_name", "")
                        if codec in ("subrip","srt","ass","ssa","webvtt","mov_text","hdmv_pgs_subtitle"):
                            subtitle_tracks.append({"index": sidx, "label": title or f"Subtitle {sidx+1}", "lang": lang, "codec": codec})
                        sidx += 1
            except Exception as e:
                logging.warning(f"ffprobe parse error: {e}")

        return web.json_response({"audio": audio_tracks, "subtitles": subtitle_tracks},
                                 headers={"Access-Control-Allow-Origin": "*"})
    except web.HTTPForbidden:
        raise
    except Exception as e:
        logging.error(f"Info handler: {e}")
        return web.json_response({"audio": [], "subtitles": [], "error": str(e)},
                                 headers={"Access-Control-Allow-Origin": "*"})

# ── /audio/{id}/{track}?hash= — remux with selected audio track ───────────────
@routes.get(r"/audio/{id:\d+}/{track:\d+}", allow_head=True)
async def audio_handler(request: web.Request):
    try:
        id          = int(request.match_info["id"])
        track_index = int(request.match_info["track"])
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

        cmd = [
            "ffmpeg", "-v", "quiet", "-nostdin",
            "-i", file_url,
            "-map", "0:v:0", "-map", f"0:a:{track_index}",
            "-c", "copy", "-f", "matroska", "pipe:1"
        ]
        proc = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        response = web.StreamResponse(status=200, headers={
            "Content-Type": "video/webm",
            "Content-Disposition": f'inline; filename="{file_id.file_name}"',
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
        })
        await response.prepare(request)
        try:
            while True:
                chunk = await proc.stdout.read(1024 * 256)
                if not chunk:
                    break
                await response.write(chunk)
        finally:
            try: proc.kill()
            except: pass
            await proc.wait()
        await response.write_eof()
        return response
    except web.HTTPForbidden:
        raise
    except ConnectionResetError:
        pass
    except Exception as e:
        logging.error(f"Audio handler: {e}")
        raise web.HTTPInternalServerError(text=str(e))

# ── /sub/{id}/{track}?hash= — extract subtitle as ASS or WebVTT ──────────────
_sub_cache: dict = {}
_sub_codec_cache: dict = {}

@routes.get(r"/sub/{id:\d+}/{track:\d+}", allow_head=True)
async def subtitle_handler(request: web.Request):
    try:
        id          = int(request.match_info["id"])
        track_index = int(request.match_info["track"])
        secure_hash = request.rel_url.query.get("hash", "")

        index = min(work_loads, key=work_loads.get)
        faster_client = multi_clients[index]
        if faster_client not in class_cache:
            class_cache[faster_client] = ByteStreamer(faster_client)
        tg_connect = class_cache[faster_client]
        file_id = await tg_connect.get_file_properties(id)
        if file_id.unique_id[:6] != secure_hash:
            raise web.HTTPForbidden(text="Invalid hash")

        cache_key = (id, track_index)
        if cache_key in _sub_cache:
            data, ctype, fmt = _sub_cache[cache_key]
            return web.Response(body=data, content_type=ctype,
                                headers={"Access-Control-Allow-Origin": "*",
                                         "X-Subtitle-Format": fmt,
                                         "Cache-Control": "public, max-age=86400"})

        from urllib.parse import quote_plus
        file_url = f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"

        codec = _sub_codec_cache.get(cache_key, "")
        if not codec:
            try:
                pp = await asyncio.create_subprocess_exec(
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_streams", "-select_streams", "s", file_url,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                pout, _ = await asyncio.wait_for(pp.communicate(), timeout=20)
                streams = _json.loads(pout).get("streams", [])
                if track_index < len(streams):
                    codec = streams[track_index].get("codec_name", "")
            except Exception:
                codec = ""

        is_ass = codec in ("ass", "ssa")
        out_fmt = "ass" if is_ass else "webvtt"
        ctype   = "text/x-ssa" if is_ass else "text/vtt"

        cmd = [
            "ffmpeg", "-nostdin", "-probesize", "50M", "-analyzeduration", "0",
            "-i", file_url, "-map", f"0:s:{track_index}", "-f", out_fmt, "pipe:1"
        ]
        proc = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill(); await proc.wait()
            raise web.HTTPGatewayTimeout(text="Subtitle extraction timed out")

        if proc.returncode != 0 or not stdout:
            err = stderr.decode(errors="replace")[:400]
            logging.warning(f"ffmpeg sub failed id={id} track={track_index}: {err}")
            raise web.HTTPNotFound(text=f"Subtitle failed: {err[:150]}")

        _sub_cache[cache_key] = (stdout, ctype, out_fmt)
        _sub_codec_cache[cache_key] = codec
        return web.Response(body=stdout, content_type=ctype,
                            headers={"Access-Control-Allow-Origin": "*",
                                     "X-Subtitle-Format": out_fmt,
                                     "Cache-Control": "public, max-age=86400"})
    except (web.HTTPForbidden, web.HTTPNotFound, web.HTTPGatewayTimeout):
        raise
    except InvalidHash:
        raise web.HTTPForbidden(text="Invalid hash")
    except Exception as e:
        logging.error(f"Subtitle handler: {e}", exc_info=True)
        raise web.HTTPInternalServerError(text=str(e))

# ── /{path} — file download/stream (ORIGINAL logic, unchanged) ────────────────
@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
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
    # ORIGINAL logic restored exactly — do not modify this function
    range_header = request.headers.get("Range", 0)

    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
    else:
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect

    file_id = await tg_connect.get_file_properties(id)

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

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'''attachment; filename="{file_name}"''',
            "Accept-Ranges": "bytes",
        },
    )
