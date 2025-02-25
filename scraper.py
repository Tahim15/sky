import os
import time
import json
import random
import logging
import asyncio
import requests
from config import *
from pyrogram import *
from bs4 import BeautifulSoup
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


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

async def extract_downlo_links(movie_url):
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
        direct_links = await get_direct_hubcloud_link(hubcloud_links[0])
        if not direct_links:
            return None
        return direct_links
    except Exception as e:
        logging.error(f"Error extracting download links from {movie_url}: {e}")
        return None

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

def setup_chromedriver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.page_load_strategy = "eager"
    options.binary_location = "/usr/bin/google-chrome"    
    driver = uc.Chrome(
        options=options,
        browser_executable_path="/usr/bin/google-chrome",
        driver_executable_path="/usr/bin/chromedriver"
    )    
    return driver

async def get_direct_hubcloud_link(hubcloud_url, max_retries=5):
    os.system("pkill -f chrome || true")
    wd = setup_chromedriver()    
    try:
        logging.info(f"🖇️ Opening {hubcloud_url}...")
        wd.get(hubcloud_url)        
        try:
            WebDriverWait(wd, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logging.info("✅ Page is fully loaded.")
        except TimeoutException:
            logging.error("❌ Page did not load within 20 seconds!")
            return []
        file_name = "Unknown File"
        try:
            file_name_element = WebDriverWait(wd, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'card-header')]"))
            )
            file_name = file_name_element.text.strip()
            logging.info(f"📁 Extracted File Name: {file_name}")
        except TimeoutException:
            logging.warning("⚠️ File name not found!")            
        retries = 0
        while retries < max_retries:
            current_url = wd.current_url
            logging.info(f"📌 Current URL: {current_url}")            
            if "hubcloud" in current_url:
                try:
                    logging.info("🔍 Searching for 'Download' Button...")
                    download_button = WebDriverWait(wd, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[@id='download']"))
                    )
                    logging.info("✅ Found 'Download' Button. Clicking...")
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
            if "hubcloud" not in wd.current_url:
                try:
                    logging.info(f"✅ New Page Detected: {wd.current_url}")
                    final_buttons = wd.find_elements(By.XPATH, "//a[contains(@class, 'btn')]")
                    final_links = [
                        btn.get_attribute("href")
                        for btn in final_buttons
                        if "Download [FSL Server]" in btn.text or "Download [PixelServer : 2]" in btn.text
                    ]
                    if final_links:
                        logging.info(f"✅ Extracted Direct Download Links: {final_links}")
                        return {"file_name": file_name, "download_links": final_links}
                    else:
                        logging.warning("⚠️ No valid download buttons found!")
                        retries += 1
                        wd.back()
                        logging.info(f"✅ Again New Page Detected: {wd.current_url}")
                        continue
                except Exception as e:
                    logging.warning(f"⚠️ Error extracting final links: {e}")
            retries += 1
        logging.error("❌ Max retries reached. Skipping this URL.")
        return {"file_name": file_name, "download_links": []}
    except Exception as e:
        logging.error(f"❌ Error processing {hubcloud_url}: {e}")
        return {"file_name": "Unknown File", "download_links": []}
    finally:
        wd.quit()
                  
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

async def scrape_skymovieshd(client):
    posted_movies = load_posted_movies() 
    movies = get_movie_links()     
    for index, movie in enumerate(movies, start=1):
        if movie['title'] in posted_movies:
            logging.info(f"⏩ Skipping {movie['title']} (Already Posted)")
            continue 
        logging.info(f"🔍 Processing: {movie['title']}")
        direct_links = await extract_download_links(movie['link'])
        if not direct_links:
            logging.warning(f"⚠️ No Valid Download Links Found For {movie['title']}.")
            continue
        message = f"<b>Recently Posted Movie ✅</b>\n\n"
        message += f"<b>{movie['title']}</b>\n\n"
        message += f"<b>Download Links:</b>\n\n"
        for data in direct_links:
            if isinstance(data, dict) and "file_name" in data and "download_links" in data:
                file_name = data["file_name"]
                download_links = data["download_links"]
                message += f"<b>{file_name}</b>\n"
                if download_links:
                    for i, link in enumerate(download_links, start=1):
                        message += f"{i}. {link}\n"
                else:
                    message += "❌ No Download Links Available\n"
                message += "\n"
        try:
            await client.send_message(chat_id=CHANNEL_ID, text=message, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
            logging.info(f"✅ Posted: {movie['title']}")
            posted_movies.append(movie['title'])
            save_posted_movies(posted_movies)
        except Exception as e:
            logging.error(f"❌ Failed To Post {movie['title']}: {e}")
        await asyncio.sleep(3)
        
async def check_new_movies(client):
    while True:
        logging.info("Checking for new movies...")
        await scrape_skymovieshd(client) 
        await asyncio.sleep(CHECK_INTERVAL)
