import asyncio
import sys
from datetime import datetime
from aiohttp import web
from pyrogram import Client
from pyrogram.enums import ParseMode
from config import *
from scraper import check_new_movies
from plugins import web_server

loop = asyncio.get_event_loop()


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=API_ID,
            workers=TG_BOT_WORKERS,
            bot_token=BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()
        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot @{usr_bot_me.username} is Running!")       
        self.loop.create_task(check_new_movies(self))       
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()
        
    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot Stopped.")


if __name__ == "__main__":
    Bot().run()
