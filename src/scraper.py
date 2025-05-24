"""
Episode link scraper for NovaStream.
"""
import re
import time
import requests
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
        r = requests.get(homepage_url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
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
        try:
            driver = get_driver()
            driver.get(homepage_url)
            time.sleep(5)
            dyn_soup = BeautifulSoup(driver.page_source, "html.parser")
            driver.quit()
            for a in dyn_soup.find_all("a", href=True):
                # match both 'ep' and 'episode' prefixes
                m = re.search(r"(?:ep(?:isode)?[-_/]?)(\d+)", a["href"], re.IGNORECASE)
                if m:
                    num = int(m.group(1))
                    full = urljoin(homepage_url, a["href"])
                    links.append((num, full))
        except Exception:
            pass

    # Deduplicate and sort by episode number
    unique = {num: url for num, url in links}
    return sorted(unique.items(), key=lambda x: x[0]) 