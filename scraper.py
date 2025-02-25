import os
import time
import json
import logging
import asyncio
import requests
import psutil
from config import *
from pyrogram import Client, enums
from bs4 import BeautifulSoup
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# Logging Setup
logging.basicConfig(level=logging.INFO)

# SkyMoviesHD Base URL
SKYMOVIESHD_URL = "https://skymovieshd.video/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# Data storage
MOVIES_FILE = "data/movies.json"
os.makedirs("data", exist_ok=True)
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump([], f)

# Load and save posted movies
def load_posted_movies():
    try:
        with open(MOVIES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_posted_movies(movies):
    with open(MOVIES_FILE, "w") as f:
        json.dump(movies, f, indent=4)

# Kill only script-launched Chrome instances
def kill_chrome():
    for process in psutil.process_iter():
        try:
            if "chrome" in process.name().lower():
                process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
kill_chrome()

# Setup ChromeDriver
def setup_chromedriver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.page_load_strategy = "eager"
    return uc.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Extract HubDrive links from Howblogs
async def extract_download_links(movie_url):
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
            if resp.status_code != 200:
                logging.error(f"Failed to load Howblogs page: {href}")
                continue

            nsoup = BeautifulSoup(resp.text, 'html.parser')
            atag = nsoup.select('div[class*="content"] a[href]')

            found_link = False
            for dl_link in atag:
                hubdrive_url = dl_link['href']
                if "hubdrive" in hubdrive_url:
                    hubdrive_links.append(hubdrive_url)
                    found_link = True

            if not found_link:
                logging.warning(f"No HubDrive links found in Howblogs page: {href}")

        if not hubdrive_links:
            return None

        return await get_direct_hubdrive_link(hubdrive_links[0])

    except Exception as e:
        logging.error(f"Error extracting download links from {movie_url}: {e}")
        return None

# Bypass HubDrive and get final download links
async def get_direct_hubdrive_link(hubdrive_url, max_retries=5):
    wd = setup_chromedriver()
    try:
        logging.info(f"🖇️ Opening {hubdrive_url}...")
        wd.get(hubdrive_url)

        WebDriverWait(wd, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        file_name = "Unknown File"
        try:
            file_name_element = WebDriverWait(wd, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'card-header')]"))
            )
            file_name = file_name_element.text.strip()
        except TimeoutException:
            logging.warning("⚠️ File name not found!")

        retries = 0
        while retries < max_retries:
            current_url = wd.current_url
            logging.info(f"📌 Current URL: {current_url}")

            if "hubdrive" in current_url:
                try:
                    download_button = WebDriverWait(wd, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Download')]"))
                    )
                    wd.execute_script("arguments[0].click();", download_button)
                    time.sleep(1)
                except TimeoutException:
                    logging.warning("⚠️ Download button not found!")
                    retries += 1
                    continue

            while len(wd.window_handles) > 1:
                wd.switch_to.window(wd.window_handles[-1])
                time.sleep(1.5)
                wd.close()
                wd.switch_to.window(wd.window_handles[0])

            if "hubdrive" not in wd.current_url:
                final_buttons = wd.find_elements(By.XPATH, "//a[contains(@class, 'btn')]")
                final_links = [btn.get_attribute("href") for btn in final_buttons if "Download" in btn.text]

                if final_links:
                    return {"file_name": file_name, "download_links": final_links}
                else:
                    retries += 1
                    wd.back()
                    continue

            retries += 1

        return {"file_name": file_name, "download_links": []}

    except Exception as e:
        logging.error(f"❌ Error processing {hubdrive_url}: {e}")
        return {"file_name": "Unknown File", "download_links": []}
    finally:
        wd.quit()

# Get movie links from SkyMoviesHD
def get_movie_links():
    try:
        response = requests.get(SKYMOVIESHD_URL, headers=HEADERS)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        movie_links = []

        for movie in soup.find_all("div", class_="Fmvideo"):
            a_tag = movie.find('a')
            if a_tag:
                title = a_tag.text.strip()
                movie_url = a_tag['href']
                movie_url = SKYMOVIESHD_URL.rstrip("/") + "/" + movie_url.lstrip("/")
                movie_links.append({"title": title, "link": movie_url})

        return movie_links
    except Exception as e:
        logging.error(f"Error getting movie links: {e}")
        return []

# Scrape and post movies
async def scrape_skymovieshd(client):
    posted_movies = load_posted_movies()
    movies = get_movie_links()

    for movie in movies:
        if movie['title'] in posted_movies:
            continue

        direct_links = await extract_download_links(movie['link'])
        if not direct_links:
            continue

        message = f"<b>{movie['title']}</b>\n\n<b>Download Links:</b>\n"
        for data in direct_links["download_links"]:
            message += f"🔗 {data}\n"

        await client.send_message(chat_id=CHANNEL_ID, text=message, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        posted_movies.append(movie['title'])
        save_posted_movies(posted_movies)
        await asyncio.sleep(3)
