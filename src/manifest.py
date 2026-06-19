"""
Manifest URL retriever for NovaStream.
"""

import time

from src.driver import close_driver, get_driver


def get_manifest_urls(url, wait=10, control=None):
    """
    Return a set of m3u8 manifest URLs found on the page.
    Uses selenium-wire to capture network requests from a headless Chrome instance.
    """
    if control and control.cancelled.is_set():
        return set()
    driver = get_driver()
    if control:
        control.register_driver(driver)
    try:
        if control and control.cancelled.is_set():
            return set()
        try:
            driver.set_page_load_timeout(max(10, wait + 5))
        except Exception:
            if control and control.cancelled.is_set():
                return set()
            pass
        driver.get(url)
        if control and control.cancelled.is_set():
            return set()
        try:
            driver.execute_script("const v = document.querySelector('video'); if(v) v.play();")
        except Exception as e:
            print(f"Warning: Failed to auto-play video: {e}")

        deadline = time.monotonic() + wait
        while True:
            if control and control.cancelled.is_set():
                return set()
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
    except Exception:
        if control and control.cancelled.is_set():
            return set()
        raise
    finally:
        if control:
            control.unregister_driver(driver)
        if not control or not control.cancelled.is_set():
            close_driver(driver)
