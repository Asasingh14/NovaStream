"""
Episode link scraper for NovaStream.
"""
import re
import time
import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from src.driver import get_driver


def find_episode_links(homepage_url):
    """
    Scrape homepage for episode links using static HTTP parse first,
    then fall back to Selenium if none are found.
    """
    # Static HTTP parse
    try:
        r = requests.get(homepage_url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        logging.warning(f"Failed to fetch homepage from {homepage_url}: {e}")
        soup = None

    links = []
    if soup:
        for a in soup.find_all("a", href=True):
            # match both 'ep' and 'episode' prefixes
            m = re.search(r"(?:ep(?:isode)?[-_/]?)(\d+)", a["href"], re.IGNORECASE)
            if m:
                num = int(m.group(1))
                full = urljoin(homepage_url, a["href"])
                links.append((num, full))

    # If none found, use Selenium to render JS
    if not links:
        driver = None
        try:
            driver = get_driver()
            driver.get(homepage_url)
            deadline = time.monotonic() + 5
            page_source = driver.page_source
            while not re.search(r"(?:ep(?:isode)?[-_/]?)(\d+)", page_source, re.IGNORECASE):
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.2)
                page_source = driver.page_source
            dyn_soup = BeautifulSoup(page_source, "html.parser")
            for a in dyn_soup.find_all("a", href=True):
                # match both 'ep' and 'episode' prefixes
                m = re.search(r"(?:ep(?:isode)?[-_/]?)(\d+)", a["href"], re.IGNORECASE)
                if m:
                    num = int(m.group(1))
                    full = urljoin(homepage_url, a["href"])
                    links.append((num, full))
        except Exception as e:
            logging.warning(f"Selenium fallback scraping failed: {e}")
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception as e:
                    logging.warning("Failed to close Selenium driver: %s", e)

    # Deduplicate and sort by episode number
    unique = {num: url for num, url in links}
    return sorted(unique.items(), key=lambda x: x[0])
