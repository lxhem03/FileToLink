# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from aiohttp import web
from .route import routes

async def web_server():
    # FIX 4: raise client_max_size for large files; the default aiohttp
    # TCPConnector allows unlimited concurrent connections (handled by the
    # event loop). No extra connector config needed — concurrency comes from
    # the async nature of aiohttp + increased Pyrogram workers in __init__.py.
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app
