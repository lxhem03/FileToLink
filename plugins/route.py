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

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("BenFilterBot")

@routes.get(r"/watch/{path:\S+}", allow_head=True)
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

# ── Shared cache ─────────────────────────────────────────────────────
# class_cache defined above

def srt_to_webvtt(srt_bytes: bytes) -> bytes:
    import re as _re
    try: text = srt_bytes.decode("utf-8-sig")
    except UnicodeDecodeError: text = srt_bytes.decode("latin-1")
    text = text.replace("\r\n","\n").replace("\r","\n").strip()
    lines = text.split("\n")
    cues, i = [], 0
    ts_pat  = _re.compile(r"^(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})")
    tag_pat = _re.compile(r"\{[^}]*\}")
    while i < len(lines):
        line = lines[i].strip()
        if _re.match(r"^\d+$", line): i+=1; continue
        m = ts_pat.match(line)
        if m:
            start,end = m.group(1).replace(",","."), m.group(2).replace(",",".")
            i+=1; cl=[]
            while i<len(lines) and lines[i].strip()!="":
                cl.append(tag_pat.sub("",lines[i])); i+=1
            if cl: cues.append(f"{start} --> {end}\n"+"\n".join(cl))
            continue
        i+=1
    return ("WEBVTT\n\n"+"\n\n".join(cues)+("\n" if cues else "")).encode("utf-8")

# ── /info/{id}?hash= ─────────────────────────────────────────────────
@routes.get(r"/info/{id:\d+}", allow_head=True)
async def info_handler(request: web.Request):
    try:
        id=int(request.match_info["id"]); secure_hash=request.rel_url.query.get("hash","")
        index=min(work_loads,key=work_loads.get); faster_client=multi_clients[index]
        if faster_client not in class_cache: class_cache[faster_client]=ByteStreamer(faster_client)
        tg=class_cache[faster_client]; file_id=await tg.get_file_properties(id)
        if file_id.unique_id[:6]!=secure_hash: raise web.HTTPForbidden(text="Invalid hash")
        from urllib.parse import quote_plus
        file_url=f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"
        cmd=["ffprobe","-v","quiet","-print_format","json","-show_streams",file_url]
        proc=await asyncio.create_subprocess_exec(*cmd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        try: stdout,_=await asyncio.wait_for(proc.communicate(),timeout=30)
        except asyncio.TimeoutError: return web.json_response({"audio":[],"subtitles":[],"error":"timeout"},headers={"Access-Control-Allow-Origin":"*"})
        audio,subs=[],[]
        if stdout:
            try:
                ai=si=0
                for s in _json.loads(stdout).get("streams",[]):
                    ct=s.get("codec_type",""); tags=s.get("tags",{})
                    lang=tags.get("language",tags.get("LANGUAGE",""))
                    title=tags.get("title",tags.get("TITLE",""))
                    if ct=="audio": audio.append({"index":ai,"label":title or f"Audio {ai+1}","lang":lang}); ai+=1
                    elif ct=="subtitle":
                        codec=s.get("codec_name","")
                        if codec in("subrip","srt","ass","ssa","webvtt","mov_text","hdmv_pgs_subtitle"):
                            subs.append({"index":si,"label":title or f"Subtitle {si+1}","lang":lang,"codec":codec})
                        si+=1
            except Exception as e: logging.warning(f"ffprobe parse: {e}")
        return web.json_response({"audio":audio,"subtitles":subs},headers={"Access-Control-Allow-Origin":"*"})
    except web.HTTPForbidden: raise
    except Exception as e: logging.error(f"info_handler: {e}"); return web.json_response({"audio":[],"subtitles":[],"error":str(e)},headers={"Access-Control-Allow-Origin":"*"})

# ── /audio/{id}/{track}?hash=&start= ─────────────────────────────────
@routes.get(r"/audio/{id:\d+}/{track:\d+}", allow_head=True)
async def audio_handler(request: web.Request):
    try:
        id=int(request.match_info["id"]); track=int(request.match_info["track"])
        secure_hash=request.rel_url.query.get("hash","")
        start_sec=float(request.rel_url.query.get("start","0") or "0")
        index=min(work_loads,key=work_loads.get); faster_client=multi_clients[index]
        if faster_client not in class_cache: class_cache[faster_client]=ByteStreamer(faster_client)
        tg=class_cache[faster_client]; file_id=await tg.get_file_properties(id)
        if file_id.unique_id[:6]!=secure_hash: raise web.HTTPForbidden(text="Invalid hash")
        from urllib.parse import quote_plus
        file_url=f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"
        cmd=["ffmpeg","-v","quiet","-nostdin"]
        if start_sec>0.5: cmd+=["-ss",str(round(start_sec,2))]
        cmd+=["-i",file_url,"-map","0:v:0","-map",f"0:a:{track}","-c","copy","-f","matroska","pipe:1"]
        proc=await asyncio.create_subprocess_exec(*cmd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        resp=web.StreamResponse(status=200,headers={"Content-Type":"video/webm","Content-Disposition":f'inline; filename="{file_id.file_name}"',
            "Access-Control-Allow-Origin":"*","Cache-Control":"no-cache","X-Audio-Track":str(track)})
        await resp.prepare(request)
        try:
            while True:
                chunk=await proc.stdout.read(1024*256)
                if not chunk: break
                await resp.write(chunk)
        finally:
            try: proc.kill()
            except: pass
            await proc.wait()
        await resp.write_eof(); return resp
    except web.HTTPForbidden: raise
    except ConnectionResetError: pass
    except Exception as e: logging.error(f"audio_handler: {e}"); raise web.HTTPInternalServerError(text=str(e))

# ── /sub/{id}/{track}?hash= ──────────────────────────────────────────
_sub_cache={}; _sub_codec_cache={}

@routes.get(r"/sub/{id:\d+}/{track:\d+}", allow_head=True)
async def sub_handler(request: web.Request):
    try:
        id=int(request.match_info["id"]); ti=int(request.match_info["track"])
        secure_hash=request.rel_url.query.get("hash","")
        index=min(work_loads,key=work_loads.get); faster_client=multi_clients[index]
        if faster_client not in class_cache: class_cache[faster_client]=ByteStreamer(faster_client)
        tg=class_cache[faster_client]; file_id=await tg.get_file_properties(id)
        if file_id.unique_id[:6]!=secure_hash: raise web.HTTPForbidden(text="Invalid hash")
        ck=(id,ti)
        if ck in _sub_cache:
            data,fmt=_sub_cache[ck]
            return web.Response(body=data,content_type="text/vtt",charset="utf-8",headers={"Access-Control-Allow-Origin":"*","Access-Control-Allow-Headers":"*","X-Subtitle-Format":fmt,"Cache-Control":"public, max-age=86400"})
        from urllib.parse import quote_plus
        file_url=f"{URL}{id}/{quote_plus(file_id.file_name)}?hash={secure_hash}"
        codec=_sub_codec_cache.get(ck,"")
        if not codec:
            try:
                pp=await asyncio.create_subprocess_exec("ffprobe","-v","quiet","-print_format","json","-show_streams","-select_streams","s",file_url,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
                po,_=await asyncio.wait_for(pp.communicate(),timeout=20)
                streams=_json.loads(po).get("streams",[])
                if ti<len(streams): codec=streams[ti].get("codec_name","")
            except: codec=""
        is_ass=codec in("ass","ssa"); fmt="ass" if is_ass else "webvtt"
        cmd=["ffmpeg","-nostdin","-probesize","50M","-analyzeduration","0","-i",file_url,"-map",f"0:s:{ti}","-f","srt","pipe:1"]
        proc=await asyncio.create_subprocess_exec(*cmd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        try: stdout,stderr=await asyncio.wait_for(proc.communicate(),timeout=120)
        except asyncio.TimeoutError: proc.kill(); await proc.wait(); raise web.HTTPGatewayTimeout(text="Subtitle timeout")
        if proc.returncode!=0 or not stdout:
            err=stderr.decode(errors="replace")[:300]; logging.warning(f"sub fail id={id} t={ti}: {err}")
            raise web.HTTPNotFound(text=f"Subtitle failed: {err[:100]}")
        vtt=srt_to_webvtt(stdout)
        _sub_cache[ck]=(vtt,fmt); _sub_codec_cache[ck]=codec
        return web.Response(body=vtt,content_type="text/vtt",charset="utf-8",headers={"Access-Control-Allow-Origin":"*","Access-Control-Allow-Headers":"*","X-Subtitle-Format":fmt,"Cache-Control":"public, max-age=86400"})
    except (web.HTTPForbidden,web.HTTPNotFound,web.HTTPGatewayTimeout): raise
    except InvalidHash: raise web.HTTPForbidden(text="Invalid hash")
    except Exception as e: logging.error(f"sub_handler: {e}",exc_info=True); raise web.HTTPInternalServerError(text=str(e))

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

# class_cache defined above

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logging.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logging.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
    logging.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(id)
    logging.debug("after calling get_file_properties")
    
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
            mime_type = mimetypes.guess_type(file_id.file_name)
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
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )
