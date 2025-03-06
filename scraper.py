import os
import json
import logging
import asyncio
import tls_client  # ✅ Use TLS Client for Cloudflare bypass
from config import *
from pyrogram import Client, enums
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

# Constants
SKYMOVIESHD_URL = "https://9xmovie.trade/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

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
        logging.warning("⚠️ No posted movies file found, creating a new one.")
        return []

# Save posted movies
def save_posted_movies(movies):
    try:
        with open(MOVIES_FILE, "w") as f:
            json.dump(movies, f, indent=4)
        logging.info("✅ Successfully saved posted movies.")
    except Exception as e:
        logging.error(f"❌ Failed to save posted movies: {e}")

# Extract Gofile.io & Streamtape.to links from Howblogs.xyz
async def extract_download_links(movie_url):
    try:
        logging.info(f"🔍 Extracting links from: {movie_url}")
        session = tls_client.Session(client_identifier="chrome_119")
        response = session.get(movie_url, headers=HEADERS)

        if response.status_code != 200:
            logging.error(f"❌ Failed to load movie page {movie_url} (Status Code: {response.status_code})")
            return None
                
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract movie title from <p> inside <figcaption>
        title_section = soup.select_one("figcaption p")
        movie_title = title_section.text.strip() if title_section else "Unknown Title"

        # Get links to linksddr.buzz pages
        howblogs_links = [link['href'] for link in soup.select('a[href*="linksddr.buzz"]')]
        if not howblogs_links:
            logging.warning(f"⚠️ No linksddr links found for {movie_url}")
            return None

        unique_links = set()
        
        for howblogs_url in howblogs_links:
            logging.info(f"🔄 Visiting Howblogs: {howblogs_url}")
            resp = session.get(howblogs_url, headers=HEADERS)
            nsoup = BeautifulSoup(resp.text, 'html.parser')

            # Extract Gofile.io & Streamtape.to links
            for dl_link in nsoup.select('a[href*="gofile.io"], a[href*="streamtape.to"]'):
                unique_links.add(dl_link['href'].strip())

        if unique_links:
            logging.info(f"✅ Extracted {len(unique_links)} links for {movie_title}")
            return [{
                "file_name": "<b>🌟 Scrapped From <a href='https://t.me/Mr_Official_300'>MovieRulZ ✅</a></b>",
                "download_links": list(unique_links)
            }]

        logging.warning(f"⚠️ No valid download links found for {movie_url}")
        return None

    except Exception as e:
        logging.error(f"❌ Error extracting download links from {movie_url}: {e}")
        return None

# Get movie links from 9xmovie.trade
async def get_movie_links():
    try:
        logging.info("🔄 Fetching latest movie links from 9xmovie.trade...")
        session = tls_client.Session(client_identifier="chrome_119")
        response = session.get(SKYMOVIESHD_URL, headers=HEADERS)

        if response.status_code != 200:
            logging.error(f"❌ Failed to load 9xmovie.trade (Status Code: {response.status_code})")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        movie_links = []

        # Select all <a> tags inside <figcaption>
        for a_tag in soup.select("figcaption a"):
            # Extract title from <p> inside <figcaption>
            title_elem = a_tag.find("p")
            title = title_elem.text.strip() if title_elem else a_tag.text.strip()

            # Get the movie URL
            movie_url = a_tag.get("href")
            if movie_url and not movie_url.startswith("http"):
                movie_url = SKYMOVIESHD_URL.rstrip("/") + "/" + movie_url.lstrip("/")
            
            movie_links.append({"title": title, "link": movie_url})

        logging.info(f"✅ Found {len(movie_links)} new movies.")
        return movie_links

    except Exception as e:
        logging.error(f"❌ Error getting movie links: {e}")
        return []

# Scrape and post movies to Telegram
async def scrape_skymovieshd(client):
    posted_movies = load_posted_movies()
    movies = await get_movie_links()

    for movie in movies:
        if movie['title'] in posted_movies:
            logging.info(f"⏭️ Skipping already posted movie: {movie['title']}")
            continue

        logging.info(f"🔍 Processing: {movie['title']}")
        direct_links = await extract_download_links(movie['link'])

        if not direct_links:
            logging.warning(f"⚠️ No valid links found for: {movie['title']}")
            continue

        message = f"<b>Recently Posted Movie ✅</b>\n\n"
        message += f"<b>{movie['title']}</b>\n\n"
        message += f"<b>Download Links:</b>\n\n"

        for data in direct_links:
            message += f"{data['file_name']}\n"
            for i, link in enumerate(data['download_links'], start=1):
                message += f"{i}. {link}\n"
            message += "\n"

        try:
            await client.send_message(CHANNEL_ID, message, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
            logging.info(f"✅ Posted {movie['title']} to Telegram.")
            posted_movies.append(movie['title'])
            save_posted_movies(posted_movies)
            await asyncio.sleep(3)
        except Exception as e:
            logging.error(f"❌ Failed to send message for {movie['title']}: {e}")

# Continuously check for new movies
async def check_new_movies(client):
    while True:
        logging.info("🔄 Checking for new movies...")
        await scrape_skymovieshd(client)
        logging.info("⏳ Waiting for the next check...")
        await asyncio.sleep(300)  # Check every 5 minutes

# Run the bot
async def main():
    logging.info("🚀 Starting Telegram bot...")
    async with Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN) as app:
        await check_new_movies(app)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"❌ Bot crashed: {e}")
