"""
Downloader module for NovaStream.
"""
import os
import re
import logging
import subprocess
import multiprocessing as mp
from multiprocessing.dummy import Pool as ThreadPool
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from colorama import init as colorama_init, Fore, Style
import tkinter as tk
from tkinter import messagebox, simpledialog
import signal

from src.manifest import get_manifest_urls
from src.scraper import find_episode_links
from src.utils import banner, expand_ranges

# initialize colorama
colorama_init(autoreset=True)

# Track ffmpeg processes for cancellation
FFMPEG_PROCS = []

def download_episode(args):
    drama_name, num, url, outdir = args
    logging.info(f"Episode {num}: starting download from {url}")
    # Fetch episode page to extract title for filename
    try:
        resp = requests.get(url)
        page_soup = BeautifulSoup(resp.text, 'html.parser')
        raw_title = page_soup.title.string.strip()
    except Exception:
        raw_title = f"Episode {num}"
    # Clean title text for filename (allow spaces only)
    title_clean = re.sub(r'[^0-9a-zA-Z ]+', ' ', raw_title).strip()
    # get manifest URL(s)
    manifests = get_manifest_urls(url)
    if not manifests:
        print(Fore.RED + f"[#{num}] No manifest found for {url}")
        return
    # pick first manifest
    m3u8 = manifests.pop()
    # Format display drama name
    drama_disp = drama_name.replace('_', ' ')
    out_filename = f"{drama_disp} - Episode {num:02d} - {title_clean}.mp4"
    outpath = os.path.join(outdir, out_filename)
    # Resume: skip if file exists
    if os.path.exists(outpath):
        msg = f"[#{num}] Skipping download; file already exists: {out_filename}"
        logging.info(msg)
        print(Fore.YELLOW + msg)
        return
    cmd = [
        "ffmpeg", "-y",
        "-i", m3u8,
        "-c", "copy",
        outpath
    ]
    # Run ffmpeg quietly and track process for cancellation
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    FFMPEG_PROCS.append(proc)
    returncode = proc.wait()
    try:
        FFMPEG_PROCS.remove(proc)
    except ValueError:
        pass
    if returncode == 0:
        msg = f"[#{num}] Download complete → {outpath}"
        logging.info(msg)
        print(Fore.GREEN + msg)
    else:
        msg = f"[#{num}] ffmpeg failed"
        logging.error(msg)
        print(Fore.RED + msg)

def run_download(url, name_input, base_output, download_all, episode_list, workers):
    banner()
    # Determine drama folder name
    drama_name = name_input.replace(" ", "_") if name_input else re.sub(r'[^0-9a-zA-Z]+','_',url.rstrip("/").split("/")[-1])
    drama_dir = os.path.join(base_output, drama_name)
    os.makedirs(drama_dir, exist_ok=True)

    # Setup file logging
    log_path = os.path.join(drama_dir, "download.log")
    logging.basicConfig(
        filename=log_path, filemode="a",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logging.info(f"Session start for '{drama_name}'")

    # Resolve episodes
    m = re.search(r"episode[-_](\d+)", url, re.IGNORECASE)
    if m:
        episodes = [(int(m.group(1)), url)]
    else:
        all_eps = find_episode_links(url)
        if not all_eps:
            if download_all:
                total = None
                def ask_total():
                    nonlocal total
                    root = tk.Tk()
                    root.withdraw()
                    total = simpledialog.askstring("Input", "Could not auto-detect episodes. Enter total count:", initialvalue="1")
                    root.destroy()
                ask_total()
                if total is None:
                    return
                all_eps = [(n, f"{url.rstrip('/')}-episode-{n}/") for n in range(1, int(total)+1)]
            elif episode_list:
                want = expand_ranges(episode_list)
                all_eps = [(n, f"{url.rstrip('/')}-episode-{n}/") for n in want]
            else:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Error", "No episodes found and no selection provided.")
                root.destroy()
                return
        episodes = all_eps if download_all else [(n,u) for n,u in all_eps if n in expand_ranges(episode_list)]

    # Parallel download
    pool_args = [(drama_name, n, u, drama_dir) for n, u in episodes]
    with mp.Pool(workers) as pool:
        for _ in tqdm(pool.imap_unordered(download_episode, pool_args), total=len(pool_args), desc="Downloading"):
            pass

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Done", f"✅ Done! {len(episodes)} files saved in:\n{drama_dir}")
    root.destroy()
    logging.info("Session complete.") 