import os
import json
import logging
import asyncio
import requests
import base64
from urllib.parse import parse_qs, urlparse
from config import *
from pyrogram import Client, enums
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO)

# Constants
SKYMOVIESHD_URL = "https://skymovieshd.farm/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
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

# Bypass HubDrive links
def hubdrive_bypass(hubdrive_url: str) -> str:
    try:
        session = requests.Session()
        session.cookies.update({'crypt': HUBDRIVE_CRYPT})

        file_id = hubdrive_url.rstrip('/').split('/')[-1]
        ajax_url = "https://hubdrive.fit/ajax.php?ajax=direct-download"

        response = session.post(ajax_url, headers={'x-requested-with': 'XMLHttpRequest'}, data={'id': file_id})

        if response.status_code != 200:
            logging.error(f"❌ HubDrive request failed! Status: {response.status_code}, Response: {response.text}")
            return None

        response_data = response.json()
        file_url = response_data.get('file', '')

        if not file_url:
            return None

        # Extract and decode Base64 Google Drive link
        parsed_url = urlparse(file_url)
        query_params = parse_qs(parsed_url.query)
        encoded_gd_link = query_params.get('gd', [''])[0]

        if not encoded_gd_link:
            return None

        decoded_gd_link = base64.b64decode(encoded_gd_link).decode('utf-8')
        return decoded_gd_link

    except Exception as e:
        logging.error(f"❌ HubDrive Bypass Error: {str(e)}")
        return None

# Get final HubDrive download link
async def get_direct_hubdrive_link(hubdrive_url):
    try:
        logging.info(f"🖇️ Processing HubDrive link: {hubdrive_url}")
        final_link = hubdrive_bypass(hubdrive_url)

        if not final_link:
            logging.error(f"❌ Failed to bypass HubDrive link: {hubdrive_url}")
            return None

        return {"file_name": "Unknown File", "download_links": [final_link]}

    except Exception as e:
        logging.error(f"❌ Error processing {hubdrive_url}: {e}")
        return None

# Extract download links from SkyMoviesHD
async def extract_download_links(movie_url):
    try:
        response = requests.get(movie_url, headers=HEADERS)
        if response.status_code != 200:
            logging.error(f"❌ Failed to load movie page {movie_url} (Status Code: {response.status_code})")
            return None
                    
        soup = BeautifulSoup(response.text, 'html.parser')
        title_section = soup.select_one('div[class^="Robiul"]')
        movie_title = title_section.text.replace('Download ', '').strip() if title_section else "Unknown Title"

        hubdrive_links = []

        # Find Howblogs links
        for link in soup.select('a[href*="howblogs.xyz"]'):
            href = link['href']
            logging.info(f"🔗 Found Howblogs Link: {href}")

            # Fetch Howblogs page
            resp = requests.get(href, headers=HEADERS)
            nsoup = BeautifulSoup(resp.text, 'html.parser')

            # Extract HubDrive links
            for dl_link in nsoup.select('a[href*="hubdrive"]'):
                hubdrive_url = dl_link['href']
                logging.info(f"✅ Found HubDrive Link: {hubdrive_url}")
                hubdrive_links.append(hubdrive_url)

        if not hubdrive_links:
            logging.warning(f"⚠️ No HubDrive links found for {movie_url}")
            return None

        direct_links = []
        for hubdrive_url in hubdrive_links:
            extracted_data = await get_direct_hubdrive_link(hubdrive_url)
            if extracted_data:
                direct_links.append(extracted_data)

        return direct_links if direct_links else None

    except Exception as e:
        logging.error(f"❌ Error extracting download links from {movie_url}: {e}")
        return None

# Get movie links from SkyMoviesHD
def get_movie_links():
    try:
        response = requests.get(SKYMOVIESHD_URL, headers=HEADERS)
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
    movies = get_movie_links()
    
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
