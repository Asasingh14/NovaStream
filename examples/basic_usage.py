#!/usr/bin/env python3
"""
Basic example script for NovaStream programmatic API.
"""

from src import run_download


def main():
    """Demo of programmatically downloading a show with NovaStream."""
    run_download(
        url="https://example.com/show",
        name_input="MyDrama",
        base_output="downloads",
        download_all=True,
        episode_list="",  # e.g., "1,3-5"
        workers=4
    )

if __name__ == "__main__":
    main() 