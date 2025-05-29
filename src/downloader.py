"""
Downloader module for NovaStream.
"""
import os
import re
import logging
import subprocess
import multiprocessing as mp
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from colorama import init as colorama_init, Fore
import tkinter as tk
from tkinter import messagebox, simpledialog

from src.manifest import get_manifest_urls
from src.scraper import find_episode_links
from src.utils import banner, expand_ranges

# initialize colorama
colorama_init(autoreset=True)

# Track ffmpeg processes for cancellation
FFMPEG_PROCS = []

def _safe_download_episode(args):
    try:
        return download_episode(args)
    except Exception as e:
        logging.error(f"Error in download_episode: {e}")
        return False

def download_episode(args):
    # Support throttle and retries if provided
    if len(args) == 4:
        drama_name, num, url, outdir = args
        throttle_kbps = 0
        retries = 0
    elif len(args) == 6:
        drama_name, num, url, outdir, throttle_kbps, retries = args
    else:
        raise ValueError(f"Invalid arguments: {args}")
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
    try:
        manifests = get_manifest_urls(url)
    except Exception as e:
        logging.error(f"Episode {num}: manifest retrieval error: {e}")
        print(Fore.RED + f"[#{num}] Manifest retrieval error: {e}")
        return False
    if not manifests:
        print(Fore.RED + f"[#{num}] No manifest found for {url}")
        return False
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
        return True
    # Build minimal working ffmpeg command
    cmd = ["ffmpeg", "-y", "-i", m3u8, "-c", "copy", outpath]
    # Run ffmpeg and capture output for better error reporting
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    FFMPEG_PROCS.append(proc)
    stdout_data, stderr_data = proc.communicate()
    returncode = proc.returncode
    try:
        FFMPEG_PROCS.remove(proc)
    except ValueError:
        pass
    if returncode == 0:
        msg = f"[#{num}] Download complete → {outpath}"
        logging.info(msg)
        print(Fore.GREEN + msg)
        return True
    else:
        err_msg = stderr_data.decode('utf-8', errors='replace').strip()
        logging.error(f"[#{num}] ffmpeg returned code {returncode}: {err_msg}")
        print(Fore.RED + f"[#{num}] ffmpeg error: {err_msg}")
        # Retry logic
        for attempt in range(1, retries+1):
            logging.info(f"[#{num}] retry {attempt}/{retries}")
            print(Fore.YELLOW + f"[#{num}] retry {attempt}/{retries}")
            # restart process
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
            FFMPEG_PROCS.append(proc)
            stdout_data, stderr_data = proc.communicate()
            returncode = proc.returncode
            try:
                FFMPEG_PROCS.remove(proc)
            except ValueError:
                pass
            if returncode == 0:
                msg = f"[#{num}] Download complete on retry {attempt} → {outpath}"
                logging.info(msg)
                print(Fore.GREEN + msg)
                return True
        # If we reach here, all retries failed
        last_err = stderr_data.decode('utf-8', errors='replace').strip()
        msg = f"[#{num}] Download failed after {retries} retries. Last error: {last_err}"
        logging.error(msg)
        print(Fore.RED + msg)
        return False

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
        for _ in tqdm(pool.imap_unordered(_safe_download_episode, pool_args), total=len(pool_args), desc="Downloading"):
            pass

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Done", f"✅ Done! {len(episodes)} files saved in:\n{drama_dir}")
    root.destroy()
    logging.info("Session complete.") 