import os
import json
import logging
import asyncio
import tls_client  # ✅ Use TLS Client for Cloudflare bypass
from config import *
from pyrogram import Client, enums
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO)

# Constants
SKYMOVIESHD_URL = "https://skymovieshd.farm/"
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
        return []

# Save posted movies
def save_posted_movies(movies):
    with open(MOVIES_FILE, "w") as f:
        json.dump(movies, f, indent=4)

# Extract Gofile.io & Streamtape.to links from Howblogs.xyz
async def extract_download_links(movie_url):
    try:
        session = tls_client.Session(client_identifier="chrome_119")

        response = session.get(movie_url, headers=HEADERS)

        if response.status_code != 200:
            logging.error(f"❌ Failed to load movie page {movie_url} (Status Code: {response.status_code})")
            return None
                    
        soup = BeautifulSoup(response.text, 'html.parser')
        title_section = soup.select_one('div[class^="Robiul"]')
        movie_title = title_section.text.replace('Download ', '').strip() if title_section else "Unknown Title"

        howblogs_links = []

        # Find Howblogs links
        for link in soup.select('a[href*="howblogs.xyz"]'):
            href = link['href']
            logging.info(f"🔗 Found Howblogs Link: {href}")
            howblogs_links.append(href)

        if not howblogs_links:
            logging.warning(f"⚠️ No Howblogs links found for {movie_url}")
            return None

        direct_links = []
        
        for howblogs_url in howblogs_links:
            # Fetch Howblogs page
            resp = session.get(howblogs_url, headers=HEADERS)
            nsoup = BeautifulSoup(resp.text, 'html.parser')

            # Extract Gofile.io & Streamtape.to links
            file_links = []
            for dl_link in nsoup.select('a[href*="gofile.io"], a[href*="streamtape.to"]'):
                file_url = dl_link['href'].strip()  # Remove any whitespace
                logging.info(f"✅ Found Direct Link: {file_url}")
                file_links.append(file_url)

            if file_links:
                direct_links.append({"file_name": "Unknown File", "download_links": file_links})

        return direct_links if direct_links else None

    except Exception as e:
        logging.error(f"❌ Error extracting download links from {movie_url}: {e}")
        return None

# Get movie links from SkyMoviesHD
async def get_movie_links():
    try:
        session = tls_client.Session(client_identifier="chrome_119")
        response = session.get(SKYMOVIESHD_URL, headers=HEADERS)

        if response.status_code != 200:
            logging.error(f"❌ Failed to load SkyMoviesHD (Status Code: {response.status_code})")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        movie_links = []

        for movie in soup.find_all("div", class_="Fmvideo"):
            a_tag = movie.find('a')
            if a_tag:
                title = a_tag.text.strip()
                movie_url = a_tag['href']
                if not movie_url.startswith("http"):
                    movie_url = SKYMOVIESHD_URL.rstrip("/") + "/" + movie_url.lstrip("/")
                movie_links.append({"title": title, "link": movie_url})

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
            continue

        logging.info(f"🔍 Processing: {movie['title']}")
        direct_links = await extract_download_links(movie['link'])

        if not direct_links:
            continue

        message = f"<b>Recently Posted Movie ✅</b>\n\n"
        message += f"<b>{movie['title']}</b>\n\n"
        message += f"<b>Download Links:</b>\n\n"

        for data in direct_links:
            message += f"<b>{data['file_name']}</b>\n"
            for i, link in enumerate(data['download_links'], start=1):
                message += f"{i}. {link}\n"
            message += "\n"

        await client.send_message(CHANNEL_ID, message, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        posted_movies.append(movie['title'])
        save_posted_movies(posted_movies)
        await asyncio.sleep(3)

# Continuously check for new movies
async def check_new_movies(client):
    while True:
        await scrape_skymovieshd(client)
        await asyncio.sleep(300)  # Check every 5 minutes

# Run the bot
async def main():
    async with Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN) as app:
        await check_new_movies(app)

if __name__ == "__main__":
    asyncio.run(main())
