import asyncio
from datetime import datetime
from aiohttp import web
from pyrogram import Client
from pyrogram.enums import ParseMode
from config import *
from scraper import check_new_movies


async def health_check(request):
    return web.Response(text="Bot is running!")

async def create_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)  
    return app

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=API_ID,
            workers=BOT_WORKERS,
            bot_token=BOT_TOKEN
        )
        self.LOGGER = LOGGER
        self.uptime = datetime.now()
        self.web_runner = None

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot @{usr_bot_me.username} is Running!")
        self.loop.create_task(check_new_movies(self))
        app = await create_web_server()
        self.web_runner = web.AppRunner(app)
        await self.web_runner.setup()
        site = web.TCPSite(self.web_runner, "0.0.0.0", PORT)
        await site.start()
        self.LOGGER(__name__).info(f"Web Server Started on PORT {PORT}!")

    async def stop(self, *args):
        if self.web_runner:
            await self.web_runner.cleanup() 
        await super().stop()
        self.LOGGER(__name__).info("Bot Stopped.")

if __name__ == "__main__":
    Bot().run()
