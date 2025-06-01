"""
Auto-update module for NovaStream.
"""

import requests
import subprocess
import sys

from src import __version__ as CURRENT_VERSION

GITHUB_REPO = "Asasingh14/NovaStream"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_latest_release():
    """Fetch the latest release information from GitHub."""
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    tag = data.get("tag_name", "")
    version = tag.lstrip("v")
    html_url = data.get("html_url", "")
    return version, html_url


def check_for_update():
    """
    Check if a newer version is available.
    Returns (latest_version, html_url) if an update exists, otherwise (None, None).
    """
    latest_version, html_url = get_latest_release()
    if latest_version and latest_version != CURRENT_VERSION:
        return latest_version, html_url
    return None, None


def perform_update():
    """Perform the update via pip install from GitHub."""
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        f"git+https://github.com/{GITHUB_REPO}.git",
    ]
    subprocess.check_call(cmd)