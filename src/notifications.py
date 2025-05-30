# notifications module for Discord integration
import os
import logging
import requests
import socket

__all__ = ['send_discord_notification', 'set_discord_webhook_url']

_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

def set_discord_webhook_url(url: str) -> None:
    """
    Set the Discord webhook URL for notifications.
    """
    global _webhook_url
    _webhook_url = url

def send_discord_notification(content: str) -> None:
    """
    Send a message to Discord via the configured webhook URL.
    If no URL is configured, does nothing.
    """
    webhook_url = _webhook_url
    if not webhook_url:
        logging.debug("Discord webhook URL not set, skipping notification")
        return
    # prefix with host name
    hostname = socket.gethostname()
    payload = {'content': f"[{hostname}] {content}"}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to send Discord notification: {e}")
