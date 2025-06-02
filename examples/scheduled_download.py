#!/usr/bin/env python3
"""
Scheduled Download Example for NovaStream API.
"""

import time
from datetime import datetime, timedelta
from src import run_download

def main():
    """
    Schedules a download to start at 2 AM local time.
    """
    target_hour = 2
    now = datetime.now()
    target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    if target_time <= now:
        target_time += timedelta(days=1)
    wait_seconds = (target_time - now).total_seconds()
    print(f"Waiting {int(wait_seconds)} seconds until {target_time}.")
    time.sleep(wait_seconds)
    run_download(
        url="https://example.com/show",
        name_input="ScheduledDrama",
        base_output="scheduled_downloads",
        download_all=True,
        episode_list="",
        workers=4
    )

if __name__ == "__main__":
    main() 