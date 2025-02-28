import os
import time
import json
import random
import logging
import asyncio
import requests
import base64
from urllib.parse import parse_qs, urlparse
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

def hubdrive_bypass(hubdrive_url: str) -> str:
    """
    Bypasses HubDrive link and retrieves the final Google Drive download link.
    """
    session = requests.Session()
    session.cookies.update({'crypt': HUBDRIVE_CRYPT})  # Set the 'crypt' cookie

    file_id = hubdrive_url.rstrip('/').split('/')[-1]  # Extract file ID

    ajax_url = "https://hubdrive.fit/ajax.php?ajax=direct-download"
    response = session.post(ajax_url, headers={'x-requested-with': 'XMLHttpRequest'}, data={'id': file_id})

    try:
        response_data = response.json()
        file_url = response_data.get('file', '')

        if not file_url:
            return "Error: No file URL found in the response."

        # Extract the Base64-encoded Google Drive link from 'gd=' query parameter
        parsed_url = urlparse(file_url)
        query_params = parse_qs(parsed_url.query)
        encoded_gd_link = query_params.get('gd', [''])[0]

        if not encoded_gd_link:
            return "Error: Google Drive link not found in response."

        # Decode the Base64-encoded Google Drive link
        decoded_gd_link = base64.b64decode(encoded_gd_link).decode('utf-8')

        return decoded_gd_link

    except Exception as e:
        return f"Error: {str(e)}"

async def get_direct_hubcloud_link(hubcloud_url):
    """
    Extracts the final download link from a HubDrive URL.
    """
    try:
        logging.info(f"🖇️ Processing HubDrive link: {hubcloud_url}")

        # Use the new bypass function
        final_link = hubdrive_bypass(hubcloud_url)

        if "Error" in final_link:
            logging.error(f"❌ Failed to bypass HubDrive link: {final_link}")
            return None

        return {"file_name": "Unknown File", "download_links": [final_link]}

    except Exception as e:
        logging.error(f"❌ Error processing {hubcloud_url}: {e}")
        return None

async def extract_download_links(movie_url):
    """
    Extracts HubDrive links from a given SkyMoviesHD movie page.
    """
    try:
        response = requests.get(movie_url, headers=HEADERS)
        if response.status_code != 200:
            logging.error(f"Failed to load movie page {movie_url} (Status Code: {response.status_code})")
            return None
                    
        soup = BeautifulSoup(response.text, 'html.parser')
        title_section = soup.select_one('div[class^="Robiul"]')
        movie_title = title_section.text.replace('Download ', '').strip() if title_section else "Unknown Title"        
        _cache = set()
        hubcloud_links = []                
        for link in soup.select('a[href*="howblogs.xyz"]'):
            href = link['href']
            if href in _cache:
                continue
            _cache.add(href)            
            resp = requests.get(href, headers=HEADERS)
            nsoup = BeautifulSoup(resp.text, 'html.parser')
            atag = nsoup.select('div[class="cotent-box"] > a[href]')            
            for dl_link in atag:
                hubcloud_url = dl_link['href']
                if "hubcloud" in hubcloud_url:
                    hubcloud_links.append(hubcloud_url)        
        if not hubcloud_links:
            logging.warning(f"No HubCloud links found for {movie_url}")
            return None        
        direct_links = []
        for hubcloud_url in hubcloud_links:
            extracted_data = await get_direct_hubcloud_link(hubcloud_url)
            if isinstance(extracted_data, dict) and "file_name" in extracted_data and "download_links" in extracted_data:
                direct_links.append(extracted_data)        
        if not direct_links:
            return None        
        return direct_links
    except Exception as e:
        logging.error(f"Error extracting download links from {movie_url}: {e}")
        return None

def get_movie_links():
    """
    Scrapes latest movie links from SkyMoviesHD.
    """
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

async def scrape_skymovieshd(client):
    """
    Scrapes and posts movies to Telegram.
    """
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

async def check_new_movies(client):
    while True:
        await scrape_skymovieshd(client)
        await asyncio.sleep(CHECK_INTERVAL)
