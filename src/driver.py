"""
Web driver module for NovaStream.
"""

# Selenium-wire and webdriver-manager imports moved into function scope for optional packaging

def get_driver():
    """Instantiate a headless Chrome WebDriver with selenium-wire."""
    # Dynamic imports to avoid bundling selenium and webdriver-manager by default
    from seleniumwire import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver 