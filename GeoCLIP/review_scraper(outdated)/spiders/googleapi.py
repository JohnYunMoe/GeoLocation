import csv
import json
import os
import re
import shutil
import time

from urllib.parse import quote_plus
from urllib.parse import urljoin

import numpy as np
from PIL import Image

import requests
import scrapy
from scrapy.http.request import Request

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) 


# API data
BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY")
BRIGHTDATA_DATASET_ID = os.getenv("BRIGHTDATA_DATASET_ID")
BRIGHTDATA_ENDPOINT = f"https://api.brightdata.com/datasets/v3/scrape?dataset_id=gd_m8ebnr0q2qlklc02fz&notify=false&include_errors=true&type=discover_new&discover_by=location"

# LOGS AND OUTPUT FILES
scraping_progress_file = "./logs/scraping_log_ar.json" # REPLACE THE _eu WITH _ar TO SAVE TO THE ARAB COUNTRIES' LOG
restaurant_details_file = "./data/restaurant_details_ar.json"
scrape_data_file = "./reviews_ar.csv"

# CONSTRAINTS
COUNTRIES = ["Saudi Arabia","United Arab Emirates","Lebanon","Egypt","Qatar"] # THE ARAB COUNTRIES
# COUNTRIES = ["Germany","United Kingdom","Italy","Spain","France"] # THE EU COUNTRIES

NUM_RESTAURANTS_PER_COUNTRY = 100 # GET 10000 RESTAURANTS PER COUNTRY
NUM_REVIEWS_THRESHHOLD = 3 # RESTAURANTS ARE PICKED ONLY IF THEIR TOTAL NUMBER OF REVIEWS EXCEED 350
NUM_IMGS_TO_DOWNLOAD = 2 # PER RESTAURANT 25 IMAGES ARE DOWNLOADED
MAX_NUM_IMGS_PER_USER = 5 # MAX NUMBER OF IMAGES SCRAPED FROM A SINGLE USER PER RESTAURANT

CITY_RESTAURANT_CNT_THRESHHOLD = 200 # DONT INCLUDE THE CITIES WHICH HAVE LESS THAN 200 RESTUARANTS LISTED ON THE WEBSITE

class GoogleSpider(scrapy.Spider):

    name = "google"

    HEADERS = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66",
        "referer": None,
    }

    def __init__(self, *args, **kwargs):
        super(GoogleSpider, self).__init__(*args, **kwargs)

        self.HEADERS = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
            # This helps skip some consent interstitials. Safe to include.
            "Cookie": "CONSENT=YES+1; PREF=hl=en",
        }

        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        try:
            # warm-up so Google sets consent cookies
            self.session.get("https://www.google.com/?hl=en", timeout=20)
        except Exception:
            pass
        
        self.scraping_progress_file = scraping_progress_file
        self.scraping_progress = self.load_progress(self.scraping_progress_file)
        self.restaurant_details_file = restaurant_details_file
        self.restaurant_details = self.load_progress(self.restaurant_details_file)

        self.scrape_data_file = scrape_data_file

    def scrape_restaurant_names_from_countries(self,countries):
        """
        Method to collect {NUM_RESTAURANTS_PER_COUNTRY} number of restaurants per country. We already have cities and number of restaurants that are listed in those cities. We use it as weights to get the proportionate number of restaurants per city. This tries to ensure an even distribution across the country.

        Further criterias include the fact that the restaurant must have atleast 350 reviews.

        Saves the restaurant names and details (feature_id, county_name, city_name, coordinates) in the self.restaurant_details_file in a json format. Used in the future for scraping from these restaurants' reviews
        """

        self.restaurant_details = self.load_progress(self.restaurant_details_file)

        # IF NO RESTAURANT RECORDS ARE ADDED, CREATE AN EMPTY CONTAINER
        if not self.restaurant_details.get('restaurants',None):
            self.restaurant_details['restaurants'] = {}

        for country_name in countries:

            print(country_name,"\n")
            cities_dict = self.restaurant_details['countries'][country_name]['cities']

            country_restaurant_count = self.restaurant_details['countries'][country_name]['country_restaurant_count']
            sampled_restaurant_count_country = self.restaurant_details['countries'][country_name].get("sampled_restaurant_count_country",0)

            # THIS IS TO BE USED WHEN YOU ARE DONE SCRAPING AND STILL CANNOT GET 400 RESTAURANTS THROUGHOUT THE COUNTRY THAT MEET YOUR CRITERIA: AS IN QATAR, LEBANON
            remaining_restaurant_count_country = NUM_RESTAURANTS_PER_COUNTRY - sampled_restaurant_count_country
            # OTHERWISE THIS IS THE DEFAULT CODE
            remaining_restaurant_count_country = NUM_RESTAURANTS_PER_COUNTRY

            #IF WE ALREADY HAVE ENOUGH RESTAURANTS, MOVE ON TO THE NEXT COUNTRY
            if sampled_restaurant_count_country >= NUM_RESTAURANTS_PER_COUNTRY:
                continue

            
            for city_name, city_detail in cities_dict.items():
                url = city_detail['url']+"#restaurant-list"

                chrome_options = webdriver.ChromeOptions()
                #chrome_options.add_argument("--headless")  # Run in headless mode (optional)

                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()), options=chrome_options
                )

                load_last_item_count = city_detail.get("last_item_count",0) # START WHERE WE LEFT OFF IN THE CITY PAGE IN RESTAURANT GURU

                # city_detail["sampled_restaurant_count_city"] = 0 # IF WE WANT TO START OVER
                sampled_restaurant_count_city = city_detail.get("sampled_restaurant_count_city",0)
                city_restaurant_count = city_detail["city_restaurant_count"]

                remaining_restaurant_count_city = int(np.ceil(remaining_restaurant_count_country * city_restaurant_count / country_restaurant_count)) - sampled_restaurant_count_city
                # CALCULATE HOW MANY RESTAURANTS NEED TO BE SCRAPED PER CITY BASED ON HOW MANY RESTAURANTS IT HAS COMPARED TO THE COUNTRY_TOTAL

                print(f"City: {city_name} Target Number of Restaurants:{int(np.ceil(remaining_restaurant_count_country * city_restaurant_count / country_restaurant_count))}. Remaining Restaurants: {remaining_restaurant_count_city}")
                
                # MORE CHECKS FOR COMPLETION OF COLLECTION
                if self.restaurant_details['countries'][country_name].get("sampled_restaurant_count_country",0) >= NUM_RESTAURANTS_PER_COUNTRY:
                    continue
                elif remaining_restaurant_count_city <=0:
                    continue

                try:
                    # FETCH THE CITY PAGE
                    driver.get(url)

                    last_item_count = 0
                    city_restaurant_cnt = 0

                    while True:
                        
                        driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")

                        try:
                            # Wait for new items to load
                            WebDriverWait(driver, 5).until(
                                lambda d: len(
                                    d.find_elements(
                                        By.CSS_SELECTOR,
                                        "div.wrapper_info",
                                    )
                                )
                                > last_item_count
                            )

                            # GET ALL ITEMS
                            items = driver.find_elements(
                                By.CSS_SELECTOR, "div.wrapper_info"
                            )
                            # PROCESS ONLY THE NEW ONES
                            if len(items)<load_last_item_count:
                                last_item_count = len(items)
                                print("Previously checked items, please wait ",last_item_count)
                                continue
                            
                            for item in items[last_item_count:]:
                                try:
                                    if city_restaurant_cnt>=remaining_restaurant_count_city:
                                        break

                                    name_element = item.find_element(
                                        By.CSS_SELECTOR, "a.notranslate.title_url"
                                    )
                                    restaurant_name = name_element.text
                                    restaurant_name = restaurant_name.replace(",","-")
                                    
                                    try:
                                        closed_or_not = item.find_element(
                                            By.CSS_SELECTOR, "div.closed_info_block"
                                        )
                                        if closed_or_not:
                                            closed_or_not = closed_or_not.text
                                            if "permanently closed" in closed_or_not.lower():
                                                continue
                                    except Exception as e:
                                        pass
                                    

                                    
                                    fid,search_url,gps_coordinates = self.get_review_page_fid_gps_from_name(restaurant_name,city_name=city_name,country_name=country_name)

                                    if not fid or not search_url or not gps_coordinates:
                                        continue
                                    

                                    if not self.restaurant_details['restaurants'].get(fid,None):
                                        self.restaurant_details['restaurants'][fid] = {"restaurant_name":restaurant_name,"city_name":city_name,"country_name":country_name,"url":search_url,"gps_coordinates":gps_coordinates}
                                        city_detail['sampled_restaurant_count_city'] = city_detail.get('sampled_restaurant_count_city',0) + 1
                                        self.restaurant_details['countries'][country_name]["sampled_restaurant_count_country"] = self.restaurant_details['countries'][country_name].get("sampled_restaurant_count_country",0) + 1
                                        if self.restaurant_details['countries'][country_name]["sampled_restaurant_count_country"] >= NUM_RESTAURANTS_PER_COUNTRY:
                                            break

                                        print(f"[FOUND] CNT:{city_detail['sampled_restaurant_count_city']}/{remaining_restaurant_count_city+sampled_restaurant_count_city} - {country_name} - {self.restaurant_details['countries'][country_name]['sampled_restaurant_count_country']}/400 --- {city_name} --- {restaurant_name}")
                                    else:
                                        continue

                                    city_restaurant_cnt+=1
                                    if city_restaurant_cnt>=remaining_restaurant_count_city:
                                        break
                                    
                                except Exception as e:
                                    print("EXCEPTION OCCURED: ",e)

                            new_item_count = len(items)

                            if city_restaurant_cnt>=remaining_restaurant_count_city:
                                new_item_count = 0
                            
                            city_detail["last_item_count"] = new_item_count
                            
                            self.save_progress(self.restaurant_details_file,self.restaurant_details)
                            
                            print(f"Processed {new_item_count - last_item_count} new items.\tCity: {city_name}, CNT: {city_restaurant_cnt}/{remaining_restaurant_count_city}")
                            last_item_count = new_item_count

                            if city_restaurant_cnt >= remaining_restaurant_count_city:
                                break

                            if self.restaurant_details['countries'][country_name]["sampled_restaurant_count_country"] >= NUM_RESTAURANTS_PER_COUNTRY:
                                break

                            # CHECK IF WE'VE REACHED THE BOTTOM
                            if driver.execute_script("return document.documentElement.scrollHeight - document.documentElement.scrollTop <= document.documentElement.clientHeight + 1;"):
                                break
                            
                        except TimeoutException:
                            print("No new items loaded, probably reached the end: URL" , url)
                            break

                    print(
                        f"Finished processing all items. Total extracted: {city_restaurant_cnt}/{remaining_restaurant_count_city}"
                    )


                finally:
                    driver.quit()

    def scrape_city_names_from_countries(self,countries):
        """Searches in restaurantguru.com for city names. Only gets the city if it has more than {CITY_RESTAURANT_CNT_THRESHHOLD} number of restaurants (200) listed on the website.
        """

        self.restaurant_details = self.load_progress(self.restaurant_details_file)

        self.restaurant_details['countries'] = {}

        for country_name in countries:
            country_dict={}

            country_search = country_name.replace(" ", "-")

            url = f"https://t.restaurantguru.com/cities-{country_search}-c/"

            chrome_options = webdriver.ChromeOptions()
            #chrome_options.add_argument("--headless")  # Run in headless mode (optional)

            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=chrome_options
            )


            try:
                driver.get(url)

                city_elements = driver.find_elements(By.CSS_SELECTOR, "ul.cities_link li")
                
                cities_dict = {}

                country_restaurant_count = 0
                for city_element in city_elements:
                    try:
                        city_link = city_element.find_element(By.CSS_SELECTOR,"a").get_attribute('href')
                        city_name = city_element.find_element(By.CSS_SELECTOR,"a").text.split("/")[0].strip()
                        city_restaurant_cnt = int(city_element.find_element(By.CSS_SELECTOR,"span.grey").text.split()[-1])

                        if city_restaurant_cnt<CITY_RESTAURANT_CNT_THRESHHOLD:
                            continue
                        
                        cities_dict[city_name]={'url':city_link,'city_restaurant_count':city_restaurant_cnt}
                        country_restaurant_count += city_restaurant_cnt

                        print(f"FOUND {len(cities_dict.keys())}: ",cities_dict[city_name])
                    except Exception as e:
                        print(f"Exception found: {e}")

                country_dict['cities'] = cities_dict
                country_dict['cities_count'] = len(cities_dict.keys())
                country_dict['country_restaurant_count'] = country_restaurant_count

            finally:
                driver.quit()
            
            self.restaurant_details['countries'][country_name] = country_dict

            
        self.save_progress(self.restaurant_details_file,self.restaurant_details)

    def _slug(s: str) -> str:
        # turn "KFC, Dubai (Branch #3)" -> "KFC+Dubai+Branch+3"
        return re.sub(r"[^\w]+", "+", s).strip("+")


    def get_review_page_fid_gps_from_name(self, restaurant_name, city_name="", country_name=""):
        if city_name:
            search_texts = [f"{restaurant_name} {city_name} {country_name}",f"{restaurant_name} restaurant {city_name} {country_name}",f"{restaurant_name} {country_name}",f"{restaurant_name} restaurant {country_name}",f"{restaurant_name} {city_name}",f"{restaurant_name} {city_name} restaurant"]
        else:
            search_texts = [f"{restaurant_name} {city_name} {country_name}",f"{restaurant_name} restaurant {city_name} {country_name}",f"{restaurant_name} {country_name}",f"{restaurant_name} restaurant {country_name}"]

        for search_text in search_texts:
            inp = [{
            "country": country_name,          
            "keyword": search_text,
            }]
            headers = {"Authorization": f"Bearer {BRIGHTDATA_API_KEY}", "Content-Type": "application/json"}

            try:
                resp = requests.post(BRIGHTDATA_ENDPOINT, headers=headers, data=json.dumps({"input": inp}), timeout=120)
                data = resp.json()
                rows = data.get("results", data if isinstance(data, list) else [])
            except Exception as e:
                print(f"Exception occured while getting fid and gps for {restaurant_name} : {e}")
                continue

            if not rows:
                continue
            row = rows[0]
            fid = row.get("fid_location")
            url = row.get("url")
            lat = row.get("lat")
            lon = row.get("lon")
            photos = row.get("photos_and_videos") or []

            # download images
            for i, img_url in enumerate(photos, 1):
                self.download_image(f"{restaurant_name}_{i}", img_url)


            return fid, url, [float(lat),float(lon)]
        return None, None, None


        
    def load_progress(self, save_file):
        """Helper method to read a dict from a json file. Currently used for ./data/restaurant_details.json and ./logs/scraping_logs.json."""
        try:
            if os.path.getsize(save_file) == 0:
                return {}
            with open(save_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_progress(self, save_file, save_data):
        """Helper method to save logs for saving progress. Dumps a dictionary holding logging information to a json file. Currently used for ./data/restaurant_details.json and ./logs/scraping_logs.json."""
        with open(save_file, "w", encoding="utf-8") as file:
            json.dump(save_data, file, ensure_ascii=False)

    def save_to_csv(self, file, row):
        """Helper method to append a row into the output csv. By default it is "./reviews.csv".
        Args:
        --------
        save_file: file path, str
        row: dict containing header, value
        """
        file_exists = os.path.isfile(file)
        with open(file, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = row.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def download_image(self, name, url):
        """Helper method to download images from a url
        """
        response = requests.get(url, stream=True)

        if not os.path.exists("./images"):
            os.makedirs("./images")
        with open(f"./images/{name}.png", "wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)

    def start_requests(self):
        """Default method called by scrapy. Use 'scrapy crawl google' command to start scraping. Loads the restaurant details form restaurant_details.json file and starts scraping for 
        reviews with images. Scraping is currently subject to constraints. At most NUM_IMAGES_PER_USER number of images (by default 3) are gathered and then it moves on to the next user. 
        Gathers NUM_IMGS_TO_DOWNLOAD number of images for each restaurant (by default 30)"""
    

        for fid in self.restaurant_details['restaurants']:
            restaurant_detail = self.restaurant_details['restaurants'][fid]

            restaurant_name = restaurant_detail["restaurant_name"]
            if fid not in self.scraping_progress:
                self.scraping_progress[fid] = {
                    "restaurant_name": restaurant_name,
                    "status": "not_started",
                    "next_page_token": "",
                    "images_left_to_download": NUM_IMGS_TO_DOWNLOAD
                }

            if self.scraping_progress[fid]["images_left_to_download"]==0:
                continue
            
            if self.scraping_progress[fid]["status"] != "completed":

                next_page_token = self.scraping_progress[fid]["next_page_token"]
                url = (
                    "https://www.google.com/async/reviewDialog?async=feature_id:"
                    + str(fid)
                    + f",next_page_token:{next_page_token}"
                    + ",_fmt:pc"
                )

                images_left_to_download = self.scraping_progress[fid]["images_left_to_download"]

                yield Request(
                    url=url,  # THE URL CONTAINS THE NEXT PAGE TOKEN, NO NEED TO SEND IT VIA META
                    headers=self.HEADERS,
                    callback=self.parse_reviews,
                    meta={
                        "feature_id":fid,
                        "restaurant_detail": restaurant_detail,
                        "images_left_to_download":images_left_to_download
                    },
                )

    def start_requests(self):
        """Default method called by scrapy. Use 'scrapy crawl google' command to start scraping. Loads the restaurant details form restaurant_details.json file and starts scraping for 
        reviews with images. Scraping is currently subject to constraints. At most NUM_IMAGES_PER_USER number of images (by default 3) are gathered and then it moves on to the next user. 
        Gathers NUM_IMGS_TO_DOWNLOAD number of images for each restaurant (by default 30)"""
    

        for fid in self.restaurant_details['restaurants']:
            restaurant_detail = self.restaurant_details['restaurants'][fid]

            restaurant_name = restaurant_detail["restaurant_name"]
            if fid not in self.scraping_progress:
                self.scraping_progress[fid] = {
                    "restaurant_name": restaurant_name,
                    "status": "not_started",
                    "next_page_token": "",
                    "images_left_to_download": NUM_IMGS_TO_DOWNLOAD
                }

            if self.scraping_progress[fid]["images_left_to_download"]==0:
                continue
            
            if self.scraping_progress[fid]["status"] != "completed":

                next_page_token = self.scraping_progress[fid]["next_page_token"]
                url = (
                    "https://www.google.com/async/reviewDialog?async=feature_id:"
                    + str(fid)
                    + f",next_page_token:{next_page_token}"
                    + ",_fmt:pc"
                )

                images_left_to_download = self.scraping_progress[fid]["images_left_to_download"]

                yield Request(
                    url=url,  # THE URL CONTAINS THE NEXT PAGE TOKEN, NO NEED TO SEND IT VIA META
                    headers=self.HEADERS,
                    callback=self.parse_reviews,
                    meta={
                        "feature_id":fid,
                        "restaurant_detail": restaurant_detail,
                        "images_left_to_download":images_left_to_download
                    },
                )

    def parse_reviews_brightdata(self, restaurant_detail: dict):
        """
        Pull reviews via Bright Data (collect-by-URL), save rows for reviews that have photos.
        Expects restaurant_detail to contain:
            - restaurant_name
            - country_name
            - city_name
            - gps_coordinates ("lat,lon")   # if you want lat/lon in the CSV
            - url (Google Maps place URL)   # input for Bright Data
        """
        

        # pull context (same as your existing code uses)
        restaurant_name = restaurant_detail["restaurant_name"]
        country_name    = restaurant_detail["country_name"]
        city_name       = restaurant_detail["city_name"]
        gps_coordinate  = restaurant_detail.get("gps_coordinates", "")
        lat = lon = None
        if gps_coordinate and "," in gps_coordinate:
            lat, lon = gps_coordinate.split(",")
            lat = float(lat); lon = float(lon)

        place_url = restaurant_detail["url"]  # the Google Maps place URL

        headers = {
            "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        }

        # Ask BD to return only what we need
        params = {
            "dataset_id": "gd_luzfs1dn2oa0teb81",
            "notify": "false",
            "include_errors": "true",
        }

        payload = {
            "input": [
                {
                    "url": place_url
                    # You said you won't use days_limit; omit it.
                    # If you ever want to cap volume: add "days_limit": N
                }
            ]
        }

        # Fire request (Bright Data often returns 200 with results or 202 with snapshot_id)
        r = requests.post(
            "https://api.brightdata.com/datasets/v3/scrape",
            headers=headers,
            params=params,
            json=payload,
            timeout=120,
        )

        # If 202, poll & download snapshot (tiny inline helper)
        def _poll_then_download(snapshot_id, timeout_sec=300, poll_every=2.0):
            base = "https://api.brightdata.com/datasets/v3"
            deadline = time.time() + timeout_sec
            while time.time() < deadline:
                pj = requests.get(f"{base}/progress/{snapshot_id}", headers=headers, timeout=30).json()
                state = (pj.get("status") or pj.get("state") or "").lower()
                if state in {"completed", "ready", "finished", "success"}:
                    sj = requests.get(f"{base}/snapshot/{snapshot_id}", headers=headers, timeout=120).json()
                    return sj.get("results", sj if isinstance(sj, list) else [])
                time.sleep(poll_every)
            return []

        if r.status_code == 202:
            snap = r.json().get("snapshot_id")
            if not snap:
                return
            rows = _poll_then_download(snap)
        else:
            data = r.json()
            rows = data.get("results", data if isinstance(data, list) else [])

        if not rows:
            return

        # For each review row:
        # We only keep rows that have photos (to match your current "image-focused" CSV)
        # Fields you requested:
        # review_id, reviewer_name, reviews_by_reviewer, reviewer_url, local_guide,
        # review_rating, review, review_date, number_of_likes, photos (array),
        # place_general_rating
        safe_name = re.sub(r"[^\w]+", "_", restaurant_name).strip("_")

        for row in rows:
            photos = row.get("photos") or []   # array of image URLs
            if not photos:
                continue  # skip reviews with no images (matches your current behavior)

            review_id            = row.get("review_id")
            reviewer_name        = (row.get("reviewer_name") or "").replace(",", "")
            reviews_by_reviewer  = row.get("reviews_by_reviewer", 0)
            reviewer_url         = row.get("reviewer_url")
            local_guide          = bool(row.get("local_guide"))
            review_rating        = row.get("review_rating")
            review_text          = (row.get("review") or "").replace("\n", " ").strip()
            review_date          = row.get("review_date")
            number_of_likes      = row.get("number_of_likes", 0)
            place_general_rating = row.get("place_general_rating")

            # Create one CSV row per photo (like your current pipeline)
            for i, img_url in enumerate(photos, 1):
                image_name = f"{safe_name}_{review_id}_{i}"
                self.download_image(image_name, img_url)

                data_row = {
                    "country_name": country_name,
                    "city_name": city_name,
                    "restaurant_name": restaurant_name,

                    # New fields from BD:
                    "review_id": review_id,
                    "reviewer": reviewer_name,
                    "reviews_by_reviewer": reviews_by_reviewer,
                    "reviewer_url": reviewer_url,
                    "local_guide": local_guide,
                    "review_rating": review_rating,
                    "review": review_text,
                    "review_date": review_date,
                    "number_of_likes": number_of_likes,
                    "place_general_rating": place_general_rating,

                    # Image bookkeeping:
                    "image_name": image_name,

                    # Keep lat/lon if you want (carried from your context):
                    "lat": lat,
                    "lon": lon,
                }
                self.save_to_csv(self.scrape_data_file, data_row)




    



spider = GoogleSpider()

'''Method to get city names from restaurantguru.com from country name'''
spider.scrape_city_names_from_countries(COUNTRIES) # WARNING: THIS MIGHT TRIGGER CPATCHAS

'''Method to get restaurant names from the city names we collected previously'''
spider.scrape_restaurant_names_from_countries(COUNTRIES)

'''Scrapy calls start_requests on it's own when "scrapy crawl google" command is passed'''
'''But if you only want to get the restaurant names or city names, use "python google.py" and it should be enough'''