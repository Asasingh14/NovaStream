"""
Web driver module for NovaStream.
"""

from importlib.util import find_spec
import logging
import os
import signal
import subprocess
import threading
import warnings

logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

# Selenium-wire and webdriver-manager imports moved into function scope for optional packaging

def get_driver():
    """Instantiate a headless Chrome WebDriver with selenium-wire."""
    if find_spec("pkg_resources") is None:
        raise RuntimeError(
            "Selenium Wire requires pkg_resources. Install it with: "
            "python -m pip install 'setuptools<81'"
        )
    # Dynamic imports to avoid bundling selenium and webdriver-manager by default
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="pkg_resources is deprecated as an API.*",
            category=UserWarning,
        )
        from seleniumwire import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    # Streaming pages often keep ads/connections alive indefinitely. Capture
    # requests without waiting for Chrome's full page-load event.
    chrome_options.page_load_strategy = "none"
    if os.name == "nt":
        popen_kw = {"creation_flags": subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        popen_kw = {"start_new_session": True}
    service = Service(ChromeDriverManager().install(), popen_kw=popen_kw)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def close_driver(driver, timeout=2):
    """Close Selenium without allowing a broken driver to block forever."""
    finished = threading.Event()

    def close():
        try:
            driver.quit()
        except Exception as e:
            logging.debug("Browser was already closed: %s", e)
        finally:
            finished.set()

    closer = threading.Thread(target=close, daemon=True)
    closer.start()
    closer.join(timeout)
    if finished.is_set():
        return

    process = getattr(getattr(driver, "service", None), "process", None)
    if process is None:
        logging.warning("Browser shutdown timed out and no driver process was available")
        return
    try:
        process.terminate()
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (AttributeError, OSError, ProcessLookupError):
            process.kill()
    except (AttributeError, OSError, ProcessLookupError):
        pass
