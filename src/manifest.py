"""
Manifest URL retriever for NovaStream.
"""

import time

from src.driver import get_driver


def get_manifest_urls(url, wait=10):
    """
    Return a set of m3u8 manifest URLs found on the page.
    Uses selenium-wire to capture network requests from a headless Chrome instance.
    """
    driver = get_driver()
    try:
        driver.get(url)
        try:
            driver.execute_script("const v = document.querySelector('video'); if(v) v.play();")
        except Exception as e:
            print(f"Warning: Failed to auto-play video: {e}")

        deadline = time.monotonic() + wait
        while True:
            manifests = set()
            for request in driver.requests:
                content_type = (
                    request.response.headers.get("content-type", "").lower()
                    if request.response
                    else ""
                )
                if (
                    "m3u8" in request.url.lower()
                    or "application/vnd.apple.mpegurl" in content_type
                ):
                    manifests.add(request.url)
            if manifests or time.monotonic() >= deadline:
                return manifests
            time.sleep(0.2)
    finally:
        driver.quit()
