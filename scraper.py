import os
import json
import logging
import asyncio
import tls_client  # ✅ Use TLS Client for Cloudflare bypass
from config import *
from pyrogram import Client, enums

# Set up logging
logging.basicConfig(level=logging.INFO)

# Constants
HB_LINKS_API = "https://hblinks.pro/wp-json/wp/v2/posts/"
MOVIES_FILE = "data/movies.json"
os.makedirs("data", exist_ok=True)
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump([], f)

# Load posted movies
def load_posted_movies():
    try:
        with open(MOVIES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Save posted movies
def save_posted_movies(movies):
    with open(MOVIES_FILE, "w") as f:
        json.dump(movies, f, indent=4)

# Extract all links from JSON API
async def extract_movie_links():
    try:
        session = tls_client.Session(client_identifier="chrome_119")
        response = session.get(HB_LINKS_API)

        if response.status_code != 200:
            logging.error(f"❌ Failed to load API (Status Code: {response.status_code})")
            return []

        movies_data = response.json()
        movie_links = []

        for movie in movies_data:
            title = movie.get("title", {}).get("rendered", "Unknown Title")
            links = [link.get("href") for link in movie.get("links", []) if "href" in link]

            if links:
                movie_links.append({"title": title, "download_links": links})

        return movie_links

    except Exception as e:
        logging.error(f"❌ Error extracting movie links: {e}")
        return []

# Scrape and post movies to Telegram
async def scrape_movies(client):
    posted_movies = load_posted_movies()
    movies = await extract_movie_links()

    for movie in movies:
        if movie["title"] in posted_movies:
            continue

        logging.info(f"🔍 Processing: {movie['title']}")

        message = f"<b>Recently Posted Movie ✅</b>\n\n"
        message += f"<b>{movie['title']}</b>\n\n"
        message += f"<b>Download Links:</b>\n\n"

        message += "<b>🌟 Scrapped From <a href='https://t.me/Mr_Official_300'>Hdhub4u ✅</a></b>\n"

        for i, link in enumerate(movie["download_links"], start=1):
            message += f"{i}. {link}\n"

        await client.send_message(CHANNEL_ID, message, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        posted_movies.append(movie["title"])
        save_posted_movies(posted_movies)
        await asyncio.sleep(3)

# Continuously check for new movies
async def check_new_movies(client):
    while True:
        await scrape_movies(client)
        await asyncio.sleep(300)  # Check every 5 minutes

# Run the bot
async def main():
    async with Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN) as app:
        await check_new_movies(app)

if __name__ == "__main__":
    asyncio.run(main())
