# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, math, logging, secrets, mimetypes, time, asyncio
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

# FIX 4: Lock per message-id so concurrent range requests for the SAME file
# don't race when populating the ByteStreamer cache. Different files/users
# are fully independent and run in parallel (aiohttp is async, no thread
# blocking occurs). The lock only serialises the *first* cache-miss per id.
_cache_locks: dict[int, asyncio.Lock] = {}

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)

    # FIX 4: pick the least-loaded client (unchanged logic, works for multi-client)
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    # FIX 4: Build/reuse ByteStreamer without a global blocking lock.
    # Each client gets its own cached instance; concurrent requests share it.
    if faster_client not in class_cache:
        class_cache[faster_client] = ByteStreamer(faster_client)
        logging.debug(f"Created new ByteStreamer for client {index}")
    tg_connect = class_cache[faster_client]

    # Per-message-id lock only for the first property fetch (cache miss).
    # Once cached, subsequent calls skip the lock entirely.
    if id not in tg_connect.cached_file_ids:
        if id not in _cache_locks:
            _cache_locks[id] = asyncio.Lock()
        async with _cache_locks[id]:
            # Double-check after acquiring lock (another coroutine may have filled it)
            if id not in tg_connect.cached_file_ids:
                await tg_connect.generate_file_properties(id)
                logging.debug(f"Cached file properties for message ID {id}")

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

    # FIX 4: increment workload counter; yield_file is an async generator so
    # it streams data without blocking the event loop for other users.
    work_loads[index] += 1
    try:
        body = tg_connect.yield_file(
            file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
        )

        mime_type = file_id.mime_type
        file_name = file_id.file_name
        disposition = "inline"  # FIX 3: use inline so browser plays video, not downloads

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

        # FIX 3: Set disposition to inline for video/audio so browsers stream it
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
        # FIX 4: Always decrement workload so the load balancer stays accurate
        work_loads[index] = max(0, work_loads[index] - 1)
