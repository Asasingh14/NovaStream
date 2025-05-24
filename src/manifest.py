"""
Manifest URL retriever for NovaStream.
"""

import time
# Selenium-wire imports moved into function scope for optional packaging


def get_manifest_urls(url, wait=10):
    """
    Return a set of m3u8 manifest URLs found on the page.
    Uses selenium-wire to capture network requests from a headless Chrome instance.
    """
    # Dynamic imports to avoid bundling selenium-wire by default
    from seleniumwire import webdriver
    from selenium.webdriver.chrome.options import Options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    # Try to auto-play video so the manifest is requested
    try:
        driver.execute_script("const v = document.querySelector('video'); if(v) v.play();")
    except Exception:
        pass

    # Wait for network requests to fire
    time.sleep(wait)

    manifests = set()
    for req in driver.requests:
        # Some responses may be missing headers
        content_type = (req.response.headers.get("content-type", "").lower()
                        if req.response else "")
        # Look for .m3u8 URLs or Apple HLS content types
        if "m3u8" in req.url.lower() or "application/vnd.apple.mpegurl" in content_type:
            manifests.add(req.url)

    driver.quit()
    return manifests 