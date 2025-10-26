r"""Google Maps Reviewer-Place Chain Scraper

Goal:
Start from a given Google Maps place URL (restaurant/POI). From its reviews:
  1. Pick the first reviewer (user profile) and open their contributions page.
  2. From that reviewer, select the SECOND restaurant they've reviewed that is
     in the target city (default: Abu Dhabi) and navigate to that place's page.
  3. On the new place's reviews, pick a different reviewer (not the one we came
     from), visit their profile, choose their second target-city restaurant, and repeat.

Intended outcome: forms a traversal chain visiting many (eventually all) places in
that city reachable via reviewer-review graph.

Notes on Fragility:
- Google Maps DOM changes frequently; all CSS/XPath selectors are heuristics.
- Reviewer profile pages and the layout for contributed reviews can vary by account.
- Some reviewers have fewer than 2 reviews in the target city; we skip them.
- Chain may loop back to already seen places; we maintain visited_place_ids.

Enhancements (not implemented but hooks present):
- Persist state to disk (checkpointing) after each hop.
- Breadth-first expansion queue instead of single chain (graph coverage).
- Parallelization with multiple drivers (riskier re: detection).

LOGIN & PROFILE PERSISTENCE:
To stay signed in, create a dedicated Chrome profile once, sign in manually, then reuse it:
  1. Close all Chrome.
  2. Run: chrome.exe --user-data-dir="C:\selenium\gprofile" --profile-directory="Profile 1"
  3. Sign in to Google, set language/UI prefs, close Chrome.
  4. Set PERSISTENT_USER_DATA_DIR / PERSISTENT_PROFILE_DIR below.
You can also pass pause_for_login=True on first run to log in, then re-run with False.
"""
from __future__ import annotations
import time
import csv
import re
from dataclasses import dataclass
from typing import Optional, List, Set
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --------------------------- Configuration ----------------------------------
TARGET_CITY = "Abu Dhabi"  # Default city filter (case-insensitive substring match)
DEFAULT_WAIT = 20
SCROLL_PAUSE = 1.2
PROFILE_SCROLL_LIMIT = 8
PLACE_REVIEWER_SCROLL_LIMIT = 6
DEBUG_DUMP = True

# Persistent profile configuration (set path to an existing signed-in profile)
PERSISTENT_USER_DATA_DIR = r"C:\selenium\gprofile"  # create & sign in first
PERSISTENT_PROFILE_DIR = "Profile 1"  # or "Default"
USE_PERSISTENT_PROFILE = True  # toggle to enable/disable

@dataclass
class ChainHop:
    hop_index: int
    place_name: str
    place_url: str
    place_id: str
    reviewer_name: str
    reviewer_profile_url: str
    chosen_next_place_name: str | None = None
    chosen_next_place_url: str | None = None

# --------------------------- Utility functions ------------------------------

def extract_place_id_from_url(url: str) -> str:
    """Heuristic extraction of a stable-ish place identifier from a Google Maps URL.
    Attempts to use the !1s segment or the ChIJ code; falls back to full URL hash.
    """
    # Look for ChIJ... pattern (Places CID style) or encoded !1sid tokens
    m = re.search(r"(ChIJ[\w-]+)", url)
    if m:
        return m.group(1)
    m2 = re.search(r"!1s([^!]+)", url)
    if m2:  
        return m2.group(1)
    return str(abs(hash(url)))

# --------------------------- Core Scraper Class -----------------------------
class GoogleMapsChainScraper:
    def __init__(self, headless: bool = False, target_city: str = TARGET_CITY, output_csv: str = "chain_results.csv", pause_for_login: bool = False):
        self.target_city = target_city.lower()
        self.output_csv = output_csv
        self.visited_place_ids: Set[str] = set()
        self.chain: List[ChainHop] = []

        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")  # login unlikely to work headless
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        if USE_PERSISTENT_PROFILE:
            options.add_argument(f"--user-data-dir={PERSISTENT_USER_DATA_DIR}")
            options.add_argument(f"--profile-directory={PERSISTENT_PROFILE_DIR}")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, DEFAULT_WAIT)

        if pause_for_login:
            self._pause_for_manual_login()

    # --------------------- Login helper -----------------------------------
    def _pause_for_manual_login(self):
        print("\n=== MANUAL LOGIN MODE ===")
        print("A Chrome window is open. Sign in to your Google account now if needed.")
        print("Press ENTER here in the console once you are fully logged in and at.")
        input("After login (and maybe loading maps.google.com manually), press ENTER to continue...")

    # --------------------- High-level public API ---------------------------
    def run_chain(self, start_place_url: str, hops: int = 10):
        """Run the reviewer->place chain starting from a given place URL."""
        self._open_url(start_place_url)
        start_place_id = extract_place_id_from_url(self.driver.current_url)
        self.visited_place_ids.add(start_place_id)
        current_place_url = self.driver.current_url

        for hop_index in range(hops):
            place_name = self._get_place_name()
            place_id = extract_place_id_from_url(current_place_url)
            print(f"[Hop {hop_index}] At place: {place_name}")

            reviewer_block = self._pick_first_reviewer()
            if not reviewer_block:
                print("  No reviewer found; terminating chain.")
                break

            reviewer_name, reviewer_profile = reviewer_block
            print(f"  Picked reviewer: {reviewer_name}")

            self._open_url(reviewer_profile)
            # Choose second restaurant in target city
            next_place = self._pick_second_place_in_city(exclude_place_id=place_id)
            if not next_place:
                print("  No valid second place in target city; terminating chain.")
                break
            next_place_name, next_place_url = next_place

            # Navigate to next place
            self._open_url(next_place_url)
            time.sleep(2)
            # Ensure it's a place (not directions / photos) by re-fetching canonical URL
            next_canonical_url = self.driver.current_url
            next_place_id = extract_place_id_from_url(next_canonical_url)
            if next_place_id in self.visited_place_ids:
                print("  Encountered already visited place; terminating to avoid loops.")
                break
            self.visited_place_ids.add(next_place_id)

            hop = ChainHop(
                hop_index=hop_index,
                place_name=place_name,
                place_url=current_place_url,
                place_id=place_id,
                reviewer_name=reviewer_name,
                reviewer_profile_url=reviewer_profile,
                chosen_next_place_name=next_place_name,
                chosen_next_place_url=next_canonical_url,
            )
            self.chain.append(hop)
            self._persist_csv_incremental(hop)

            # Prepare for next iteration
            current_place_url = next_canonical_url
        print("Chain complete. Total hops:", len(self.chain))

    # --------------------- Place page helpers ------------------------------
    def _get_place_name(self) -> str:
        try:
            el = self.wait.until(EC.presence_of_element_located((By.XPATH, '//h1[contains(@class, "fontHeadlineLarge") or @role="heading"]')))
            return el.text.strip()
        except Exception:
            return ""

    def _open_reviews_panel(self):
        try:
            reviews_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "reviews") or contains(., "Reviews")]')))
            reviews_button.click()
            time.sleep(2)
        except Exception:
            pass  # Panel may already be open
        
    def _debug_dump_reviews_container(self, container) -> None:
        """Print and save a readable snapshot of the reviews container."""
        try:
            html = container.get_attribute("outerHTML") or ""
            pretty = BeautifulSoup(html, "html.parser").prettify()
            # Print a truncated view to console
            print("\n[DEBUG] Reviews container (truncated):")
            print(pretty[:3000] + ("\n...[truncated]..." if len(pretty) > 3000 else ""))

            # List immediate children tags/classes
            kids = container.find_elements(By.XPATH, "./*")
            print(f"\n[DEBUG] Immediate children count: {len(kids)}")
            for i, k in enumerate(kids[:25]):  # limit to first 25
                print(f"  [{i}] <{k.tag_name}> id='{k.get_attribute('id')}' class='{k.get_attribute('class')}'")

            # Save full HTML and a screenshot for offline inspection
            with open("container_dump.html", "w", encoding="utf-8") as f:
                f.write(pretty)
            try:
                container.screenshot("container.png")
            except Exception:
                pass
            print("\n[DEBUG] Saved container_dump.html and container.png in current working directory.")
        except Exception as e:
            print(f"[DEBUG] Failed to dump container: {e}")

    def _pick_first_reviewer(self) -> Optional[tuple[str, str]]:
        """Open reviews panel (if needed) and return (reviewer_name, reviewer_profile_url)."""
        self._open_reviews_panel()
        # Scroll some to load reviews
        container = self._locate_reviews_scroll_container()
        if DEBUG_DUMP and container:
            self._debug_dump_reviews_container(container)  # human-readable dump
        if container:
            for _ in range(2):
                self.driver.execute_script('arguments[0].scrollTop = arguments[0].scrollTop + 800;', container)
                time.sleep(SCROLL_PAUSE)
        reviewers = []
        if container:
            reviewers = container.find_elements(
                By.XPATH,
                './/a[starts-with(@href, "https://www.google.com/maps/contrib/")]'
            )
        # Fallback (page-wide) if container-based search found nothing
        if not reviewers:
            reviewers = self.driver.find_elements(
                By.XPATH,
                '//a[starts-with(@href, "https://www.google.com/maps/contrib/")]'
            )
        if not reviewers:
            return None
        first = reviewers[0]
        name = first.get_attribute("aria-label") or first.text.strip() or "Unknown Reviewer"
        profile_url = first.get_attribute("href")
        return name, profile_url

    def _locate_reviews_scroll_container(self):
        try:
            return self.driver.find_element(By.XPATH, '//div[contains(@class, "m6QErb") and contains(@class, "DxyBCb") and contains(@class, "kA9KIf")]')
        except Exception:
            return None

    # --------------------- Reviewer profile helpers -----------------------
    def _pick_second_place_in_city(self, exclude_place_id: str) -> Optional[tuple[str, str]]:
        """From reviewer profile, find the second place card matching target city.
        exclude_place_id: skip if matches current place.
        Returns (place_name, place_url)."""
        # Heuristic scroll container for contributions
        for _ in range(PROFILE_SCROLL_LIMIT):
            places = self.driver.find_elements(By.XPATH, '//a[contains(@href, "/maps/place/") and descendant::div[contains(@class, "fontBodyMedium")]]')
            filtered_cards = []
            for a in places:
                url = a.get_attribute("href")
                candidate_id = extract_place_id_from_url(url)
                if candidate_id == exclude_place_id:
                    continue
                city_match = self._card_city_text(a)
                if city_match and self.target_city in city_match.lower():
                    filtered_cards.append(a)
            if len(filtered_cards) >= 2:
                second = filtered_cards[1]
                place_name = second.text.split('\n')[0].strip()
                return place_name, second.get_attribute("href")
            # Scroll further
            self.driver.execute_script('window.scrollBy(0, 800);')
            time.sleep(SCROLL_PAUSE)
        return None

    def _card_city_text(self, anchor_el) -> Optional[str]:
        try:
            # Find a span/div that likely contains address or city
            txt = anchor_el.text
            # simple heuristic: lines after first often contain city
            lines = [l.strip() for l in txt.split('\n') if l.strip()]
            if len(lines) >= 2:
                return lines[-1]
            return None
        except Exception:
            return None

    # --------------------- Output persistence -----------------------------
    def _persist_csv_incremental(self, hop: ChainHop):
        header = ["hop_index", "place_name", "place_url", "place_id", "reviewer_name", "reviewer_profile_url", "next_place_name", "next_place_url"]
        write_header = False
        try:
            with open(self.output_csv, 'r', encoding='utf-8') as _:
                pass
        except FileNotFoundError:
            write_header = True
        with open(self.output_csv, 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(header)
            w.writerow([
                hop.hop_index,
                hop.place_name,
                hop.place_url,
                hop.place_id,
                hop.reviewer_name,
                hop.reviewer_profile_url,
                hop.chosen_next_place_name,
                hop.chosen_next_place_url,
            ])

    # --------------------- Low-level helpers ------------------------------
    def _open_url(self, url: str):
        self.driver.get(url)
        time.sleep(2)

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass

# --------------------------- Script Entrypoint ------------------------------
if __name__ == "__main__":
    START_PLACE = "https://maps.app.goo.gl/bEA8FDgkqYQsdfsk6"  # Example; replace with valid place URL.
    scraper = GoogleMapsChainScraper(headless=False, target_city="Abu Dhabi", output_csv="abu_dhabi_chain.csv", pause_for_login=False)
    try:
        scraper.run_chain(START_PLACE, hops=5)
    finally:
        scraper.close()
