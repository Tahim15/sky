import os
import json
import logging
import asyncio
import requests
from urllib.parse import parse_qs, urlparse
import base64
from config import *
from pyrogram import Client, enums
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)

SKYMOVIESHD_URL = "https://skymovieshd.video/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

MOVIES_FILE = "data/movies.json"
os.makedirs("data", exist_ok=True)
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump([], f)

def load_posted_movies():
    try:
        with open(MOVIES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [] 

def save_posted_movies(movies):
    with open(MOVIES_FILE, "w") as f:
        json.dump(movies, f, indent=4)

def hubdrive_bypass(hubdrive_url: str, hubdrive_crypt: str) -> str:
    session = requests.Session()
    session.cookies.update({'crypt': hubdrive_crypt})  

    file_id = hubdrive_url.rstrip('/').split('/')[-1]  
    ajax_url = "https://hubdrive.fit/ajax.php?ajax=direct-download"
    response = session.post(ajax_url, headers={'x-requested-with': 'XMLHttpRequest'}, data={'id': file_id})

    try:
        response_data = response.json()
        file_url = response_data.get('file', '')

        if not file_url:
            return None

        parsed_url = urlparse(file_url)
        query_params = parse_qs(parsed_url.query)
        encoded_gd_link = query_params.get('gd', [''])[0]

        if not encoded_gd_link:
            return None

        decoded_gd_link = base64.b64decode(encoded_gd_link).decode('utf-8')
        return decoded_gd_link

    except Exception as e:
        logging.error(f"HubDrive bypass error: {e}")
        return None

async def extract_download_links(movie_url, hubdrive_crypt):
    try:
        response = requests.get(movie_url, headers=HEADERS)
        if response.status_code != 200:
            logging.error(f"Failed to load movie page {movie_url} (Status Code: {response.status_code})")
            return None  

        soup = BeautifulSoup(response.text, 'html.parser')
        title_section = soup.select_one('div[class^="Robiul"]')
        movie_title = title_section.text.replace('Download ', '').strip() if title_section else "Unknown Title"

        _cache = set()
        hubdrive_links = []

        for link in soup.select('a[href*="howblogs.xyz"]'):
            href = link['href']
            if href in _cache:
                continue
            _cache.add(href)

            resp = requests.get(href, headers=HEADERS)
            nsoup = BeautifulSoup(resp.text, 'html.parser')
            atag = nsoup.select('div[class="cotent-box"] > a[href]')

            for dl_link in atag:
                hubdrive_url = dl_link['href']
                if "hubdrive" in hubdrive_url:
                    hubdrive_links.append(hubdrive_url)

        if not hubdrive_links:
            logging.warning(f"No HubDrive links found for {movie_url}")
            return None  

        direct_links = []
        for hubdrive_url in hubdrive_links:
            final_link = hubdrive_bypass(hubdrive_url, hubdrive_crypt)
            if final_link:
                direct_links.append(final_link)

        if not direct_links:
            return None

        return {"movie_title": movie_title, "download_links": direct_links}

    except Exception as e:
        logging.error(f"Error extracting download links from {movie_url}: {e}")
        return None

def get_movie_links():
    try:
        response = requests.get(SKYMOVIESHD_URL, headers=HEADERS)
        if response.status_code != 200:
            logging.error(f"Failed to load SkyMoviesHD (Status Code: {response.status_code})")
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
        logging.error(f"Error getting movie links: {e}")
        return []

async def scrape_skymovieshd(client, hubdrive_crypt):
    posted_movies = load_posted_movies() 
    movies = get_movie_links()  

    for movie in movies:
        if movie['title'] in posted_movies:
            logging.info(f"⏩ Skipping {movie['title']} (Already Posted)")
            continue 

        logging.info(f"🔍 Processing: {movie['title']}")
        direct_links = await extract_download_links(movie['link'], hubdrive_crypt)

        if not direct_links:
            logging.warning(f"⚠️ No Valid Download Links Found For {movie['title']}.")
            continue

        message = f"<b>Recently Posted Movie ✅</b>\n\n"
        message += f"<b>{direct_links['movie_title']}</b>\n\n"
        message += f"<b>Download Links:</b>\n\n"

        for i, link in enumerate(direct_links["download_links"], start=1):
            message += f"{i}. {link}\n"

        try:
            await client.send_message(chat_id=CHANNEL_ID, text=message, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
            logging.info(f"✅ Posted: {direct_links['movie_title']}")
            posted_movies.append(direct_links['movie_title'])
            save_posted_movies(posted_movies)

        except Exception as e:
            logging.error(f"❌ Failed To Post {direct_links['movie_title']}: {e}")

        await asyncio.sleep(3)

async def check_new_movies(client, hubdrive_crypt):
    while True:
        logging.info("Checking for new movies...")
        await scrape_skymovieshd(client, hubdrive_crypt)
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    print("=== HubDrive Bypass Script ===")
    hubdrive_crypt = input("Enter 'crypt' cookie value: ").strip()

    app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

    async def run_bot():
        async with app:
            await check_new_movies(app, hubdrive_crypt)

    asyncio.run(run_bot())
