"""
Downloader module for NovaStream.
"""
import os
import re
import logging
import subprocess  # nosec B404
import multiprocessing as mp
import signal
import threading
import unicodedata
from dataclasses import dataclass
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
_FFMPEG_PROCS_LOCK = threading.Lock()


@dataclass(frozen=True)
class DownloadSummary:
    drama_dir: str
    total: int
    succeeded: int
    failed: int

    @property
    def successful(self):
        return self.failed == 0


class DownloadControl:
    """Cancellation state and process ownership for one download job."""

    def __init__(self):
        self.cancelled = threading.Event()
        self._processes = set()
        self._lock = threading.Lock()

    def register(self, proc):
        with self._lock:
            self._processes.add(proc)

    def unregister(self, proc):
        with self._lock:
            self._processes.discard(proc)

    def cancel(self):
        self.cancelled.set()
        with self._lock:
            processes = list(self._processes)
        for proc in processes:
            _terminate_process(proc)


def _register_process(proc, control=None):
    with _FFMPEG_PROCS_LOCK:
        FFMPEG_PROCS.append(proc)
    if control:
        control.register(proc)


def _unregister_process(proc, control=None):
    with _FFMPEG_PROCS_LOCK:
        try:
            FFMPEG_PROCS.remove(proc)
        except ValueError:
            pass
    if control:
        control.unregister(proc)


def _terminate_process(proc):
    """Terminate an ffmpeg process group on both POSIX and Windows."""
    try:
        if proc.poll() is not None:
            return
    except AttributeError:
        pass

    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (AttributeError, OSError, ProcessLookupError):
        try:
            proc.terminate()
        except (AttributeError, OSError, ProcessLookupError):
            pass


def _run_ffmpeg(cmd, control=None):
    popen_kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **popen_kwargs)  # nosec B603
    _register_process(proc, control)
    try:
        _, stderr_data = proc.communicate()
        return proc.returncode, stderr_data
    finally:
        _unregister_process(proc, control)


def _remove_partial(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as e:
        logging.warning("Could not remove partial download %s: %s", path, e)


def sanitize_path_component(value, fallback="download"):
    """Return a portable, traversal-safe filename or directory component."""
    value = str(value or "")
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", value)
    value = "".join(
        character
        if (
            character.isalnum()
            or unicodedata.category(character).startswith("M")
            or character in " .()-_"
        )
        else " "
        for character in value
    )
    value = re.sub(r"\s+", " ", value).strip(" .")
    if value.upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        value = f"_{value}"
    return (value or fallback)[:120]

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
        control = None
    elif len(args) == 7:
        drama_name, num, url, outdir, throttle_kbps, retries, control = args
    else:
        raise ValueError(f"Invalid arguments: {args}")
    if len(args) == 4:
        control = None
    logging.info(f"Episode {num}: starting download from {url}")
    # Fetch episode page to extract title for filename
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        page_soup = BeautifulSoup(resp.text, 'html.parser')
    except requests.RequestException as e:
        logging.warning(f"Failed to fetch page content from {url}: {e}")
        raw_title = f"Episode {num}"
    else:
        raw_title = page_soup.title.get_text(" ", strip=True) if page_soup.title else f"Episode {num}"
        raw_title = raw_title or f"Episode {num}"
    # Clean title text for filename (allow spaces only)
    title_clean = sanitize_path_component(raw_title, fallback=f"Episode {num}")
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
    # Prefer a master playlist, then choose deterministically.
    m3u8 = sorted(
        manifests,
        key=lambda item: ("master" not in item.lower(), item.lower()),
    )[0]
    # Format display drama name
    drama_disp = sanitize_path_component(drama_name.replace('_', ' '), fallback="Drama")
    out_filename = f"{drama_disp} - Episode {num:02d} - {title_clean}.mp4"
    outpath = os.path.join(outdir, out_filename)
    stem, ext = os.path.splitext(outpath)
    partial_path = f"{stem}.part{ext}"
    # Resume: skip if file exists
    if os.path.exists(outpath):
        msg = f"[#{num}] Skipping download; file already exists: {out_filename}"
        logging.info(msg)
        print(Fore.YELLOW + msg)
        return True
    # Always write to a temporary file and publish atomically on success.
    cmd = ["ffmpeg", "-y", "-i", m3u8, "-c", "copy", partial_path]
    _remove_partial(partial_path)
    if control and control.cancelled.is_set():
        return False
    try:
        returncode, stderr_data = _run_ffmpeg(cmd, control)
    except FileNotFoundError:
        msg = "ffmpeg was not found. Install ffmpeg and ensure it is available on PATH."
        logging.error(msg)
        print(Fore.RED + f"[#{num}] {msg}")
        return False
    if returncode == 0:
        if not os.path.exists(partial_path):
            msg = f"[#{num}] ffmpeg reported success but created no output file"
            logging.error(msg)
            print(Fore.RED + msg)
            return False
        os.replace(partial_path, outpath)
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
            _remove_partial(partial_path)
            if control and control.cancelled.is_set():
                return False
            returncode, stderr_data = _run_ffmpeg(cmd, control)
            if returncode == 0:
                if not os.path.exists(partial_path):
                    logging.error("[#%s] ffmpeg retry created no output file", num)
                    continue
                os.replace(partial_path, outpath)
                msg = f"[#{num}] Download complete on retry {attempt} → {outpath}"
                logging.info(msg)
                print(Fore.GREEN + msg)
                return True
        # If we reach here, all retries failed
        last_err = stderr_data.decode('utf-8', errors='replace').strip()
        msg = f"[#{num}] Download failed after {retries} retries. Last error: {last_err}"
        logging.error(msg)
        print(Fore.RED + msg)
        _remove_partial(partial_path)
        return False

def run_download(url, name_input, base_output, download_all, episode_list, workers):
    banner()
    # Determine drama folder name
    raw_name = name_input or re.sub(r'[^0-9a-zA-Z]+', '_', url.rstrip("/").split("/")[-1])
    drama_name = sanitize_path_component(raw_name, fallback="download").replace(" ", "_")
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
        if download_all:
            episodes = all_eps
        else:
            try:
                requested = set(expand_ranges(episode_list))
            except (TypeError, ValueError):
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Error", "Episode selection must look like 1,3-5.")
                root.destroy()
                return None
            episodes = [(number, episode_url) for number, episode_url in all_eps if number in requested]

    if not episodes:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", "No matching episodes were found.")
        root.destroy()
        return None

    # Parallel download
    pool_args = [(drama_name, n, u, drama_dir) for n, u in episodes]
    results = []
    with mp.Pool(max(1, int(workers))) as pool:
        results.extend(
            tqdm(
                pool.imap_unordered(_safe_download_episode, pool_args),
                total=len(pool_args),
                desc="Downloading",
            )
        )

    succeeded = sum(result is True for result in results)
    failed = len(episodes) - succeeded
    summary = DownloadSummary(
        drama_dir=drama_dir,
        total=len(episodes),
        succeeded=succeeded,
        failed=failed,
    )

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Done",
        f"✅ Done! {succeeded} succeeded, {failed} failed. Files saved in:\n{drama_dir}",
    )
    root.destroy()
    logging.info("Session complete: %s succeeded, %s failed.", succeeded, failed)
    return summary
