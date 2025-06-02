#!/usr/bin/env python3
"""
CSV Batch Download Example for NovaStream API.
"""

import csv
from src import run_download

def main():
    """
    Reads a CSV file 'downloads.csv' with columns:
    url,name,base_output,download_all,episode_list,workers
    and runs downloads for each row.
    """
    with open('downloads.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            run_download(
                url=row['url'],
                name_input=row.get('name', ''),
                base_output=row.get('base_output', 'downloads'),
                download_all=row.get('download_all', '').lower() in ('true','1','yes'),
                episode_list=row.get('episode_list', ''),
                workers=int(row.get('workers', 4))
            )

if __name__ == "__main__":
    main() 