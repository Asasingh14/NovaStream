"""
GUI application for NovaStream.
"""
import tkinter as tk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pkg_resources
import multiprocessing as mp
import os
import re
import time
from threading import Thread
from multiprocessing.dummy import Pool as ThreadPool
import shutil
import signal
from src.downloader import FFMPEG_PROCS

from src.scraper import find_episode_links
from src.utils import expand_ranges
from src.downloader import download_episode


def main():
    root = tk.Tk()
    root.title("NovaStream")
    # Set window icon
    try:
        # Load bundled icon.png from package data
        icon_path = pkg_resources.resource_filename(__name__, 'icon.png')
        root.iconphoto(False, tk.PhotoImage(file=icon_path))
    except:
        pass

    # Menubar
    menubar = tk.Menu(root)
    file_menu = tk.Menu(menubar, tearoff=False)
    file_menu.add_command(label="Exit", command=root.destroy)
    menubar.add_cascade(label="File", menu=file_menu)
    help_menu = tk.Menu(menubar, tearoff=False)
    help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
        "About", "NovaStream v1.0\n© 2025 Asa"))
    menubar.add_cascade(label="Help", menu=help_menu)
    root.config(menu=menubar)

    # Header with logo
    header = ttk.Frame(root, padding=(10,10))
    header.grid(row=0, column=0, sticky="EW")
    try:
        logo = tk.PhotoImage(file='logo.png')
        ttk.Label(header, image=logo).grid(row=0, column=0)
        header.image = logo
    except:
        ttk.Label(header, text="NovaStream", font=("Segoe UI", 16)).grid(row=0, column=0)

    # Main content frame
    main_frame = ttk.Frame(root, padding=(20,10))
    main_frame.grid(row=1, column=0, sticky="NSEW")
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)

    # Status bar
    status_bar = ttk.Label(root, text="Ready", relief="sunken", anchor="w")
    status_bar.grid(row=2, column=0, sticky="EW")

    # Variables
    url_var = tk.StringVar()
    name_var = tk.StringVar()
    output_var = tk.StringVar(value="downloads")
    all_var = tk.BooleanVar(value=True)
    episodes_var = tk.StringVar()
    workers_var = tk.IntVar(value=mp.cpu_count())

    # Input fields
    ttk.Label(main_frame, text="Drama URL:").grid(row=0, column=0, sticky="E", pady=5)
    ttk.Entry(main_frame, textvariable=url_var, width=40).grid(row=0, column=1, columnspan=2, sticky="EW", pady=5)

    ttk.Label(main_frame, text="Drama Name:").grid(row=1, column=0, sticky="E", pady=5)
    ttk.Entry(main_frame, textvariable=name_var, width=40).grid(row=1, column=1, columnspan=2, sticky="EW", pady=5)

    ttk.Label(main_frame, text="Output Folder:").grid(row=2, column=0, sticky="E", pady=5)
    ttk.Entry(main_frame, textvariable=output_var, width=30).grid(row=2, column=1, sticky="EW", pady=5)
    ttk.Button(main_frame, text="Browse...", command=lambda: output_var.set(filedialog.askdirectory())).grid(row=2, column=2, sticky="W", padx=5)

    all_check = ttk.Checkbutton(main_frame, text="Download ALL episodes", variable=all_var)
    all_check.grid(row=3, column=0, columnspan=3, sticky="W", pady=5)

    ttk.Label(main_frame, text="Episodes (e.g. 1,3-5):").grid(row=4, column=0, sticky="E", pady=5)
    episodes_entry = ttk.Entry(main_frame, textvariable=episodes_var, width=40)
    episodes_entry.grid(row=4, column=1, columnspan=2, sticky="EW", pady=5)

    ttk.Label(main_frame, text="Workers:").grid(row=5, column=0, sticky="E", pady=5)
    ttk.Spinbox(main_frame, from_=1, to=mp.cpu_count(), textvariable=workers_var, width=5).grid(row=5, column=1, sticky="W", pady=5)

    main_frame.columnconfigure(1, weight=1)

    cancel_flag = {'canceled': False}

    # Buttons row
    btn_frame = ttk.Frame(main_frame)
    btn_frame.grid(row=6, column=0, columnspan=3, pady=(10,0))
    start_btn = ttk.Button(btn_frame, text="Start")
    start_btn.pack(side="right", padx=5)

    def download_series():
        # Modal progress dialog
        progress_win = tk.Toplevel(root)
        progress_win.title("Downloading...")
        progress_win.resizable(False, False)
        ttk.Label(progress_win, text="Starting...").pack(padx=10, pady=(10,0))
        prog = ttk.Progressbar(progress_win, orient="horizontal", length=300, mode="indeterminate")
        prog.pack(padx=10, pady=10)
        prog.start()
        stat = ttk.Label(progress_win, text="")
        stat.pack(padx=10, pady=(0,10))
        progress_win.transient(root)
        progress_win.grab_set()
        # Reference holder for thread pool to allow immediate termination on cancel
        pool_holder = {'pool': None}
        # Add Cancel button in progress popup
        cancel_btn_popup = ttk.Button(progress_win, text="Cancel")
        cancel_btn_popup.pack(pady=(0,10))
        def on_popup_cancel():
            cancel_flag['canceled'] = True
            cancel_btn_popup.config(text="Cancelling...", state="disabled")
            stat.config(text="Cancelling...")
            try:
                prog.stop()
            except Exception:
                pass
            # Kill running ffmpeg processes
            for proc in FFMPEG_PROCS[:]:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception:
                    pass
            FFMPEG_PROCS.clear()
            # Terminate the thread pool immediately
            if pool_holder['pool'] is not None:
                pool_holder['pool'].terminate()
                pool_holder['pool'] = None
            progress_win.update_idletasks()
        cancel_btn_popup.config(command=on_popup_cancel)
        # Schedule initial status on the main thread
        progress_win.after(0, lambda: stat.config(text="Fetching episode list..."))

        # Gather parameters
        url = url_var.get().strip()
        name_input = name_var.get().strip()
        base_output = output_var.get().strip() or "downloads"
        download_all = bool(all_var.get())
        episode_list = episodes_var.get().strip()
        worker_count = workers_var.get()
        # Determine drama folder
        drama_name = name_input.replace(" ", "_") if name_input else re.sub(r'[^0-9a-zA-Z]+','_',url.rstrip("/").split("/")[-1])
        drama_dir = os.path.join(base_output, drama_name)
        os.makedirs(drama_dir, exist_ok=True)
        # Resolve episodes
        m = re.search(r"episode[-_](\d+)", url, re.IGNORECASE)
        if m:
            episodes = [(int(m.group(1)), url)]
        else:
            eps = find_episode_links(url)
            if not eps and download_all:
                total = simpledialog.askinteger("Total Episodes", "Could not auto-detect episodes. Enter total count:", initialvalue=1, parent=root)
                if not total:
                    progress_win.destroy()
                    status_bar.config(text="Canceled")
                    return
                eps = [(n, f"{url.rstrip('/')}-episode-{n}/") for n in range(1, total+1)]
            elif not eps and episode_list:
                want = expand_ranges(episode_list)
                eps = [(n, f"{url.rstrip('/')}-episode-{n}/") for n in want]
            else:
                eps = eps
            episodes = eps if download_all else [(n,u) for n,u in eps if n in expand_ranges(episode_list)]
        total = len(episodes)
        # Switch progress bar to determinate now that total is known
        def switch_to_determinate():
            prog.stop()
            prog.config(mode="determinate", maximum=total, value=0)
            stat.config(text=f"Downloading 0/{total} episodes")
        progress_win.after(0, switch_to_determinate)
        # Prepare pool arguments
        pool_args = [(drama_name, num, u, drama_dir) for num, u in episodes]
        pool = ThreadPool(worker_count)
        # Store pool reference for cancellation
        pool_holder['pool'] = pool
        completed = 0
        for _ in pool.imap_unordered(download_episode, pool_args):
            if cancel_flag['canceled']:
                pool.terminate()
                # Cancel cleanup
                try:
                    shutil.rmtree(drama_dir, ignore_errors=True)
                except Exception:
                    pass
                status_bar.config(text="Canceled (cleanup done)")
                progress_win.destroy()
                # Re-enable widgets after cancellation
                start_btn.config(state="normal")
                for child in main_frame.winfo_children():
                    try:
                        child.state(['!disabled'])
                    except Exception:
                        pass
                menubar.entryconfig("File", state="normal")
                menubar.entryconfig("Help", state="normal")
                cancel_flag['canceled'] = False
                return
            completed += 1
            # Update progress and force redraw
            def update_progress(c=completed, t=total):
                stat.config(text=f"Downloaded {c}/{t} episodes")
                prog.config(value=c)
                progress_win.update_idletasks()
            progress_win.after(0, update_progress)

        # Completed downloads
        pool.close()
        pool.join()
        status_bar.config(text="Completed")
        progress_win.destroy()
        # Re-enable widgets after completion
        start_btn.config(state="normal")
        for child in main_frame.winfo_children():
            try:
                child.state(['!disabled'])
            except Exception:
                pass
        menubar.entryconfig("File", state="normal")
        menubar.entryconfig("Help", state="normal")
        cancel_flag['canceled'] = False

    def on_start():
        start_btn.config(state="disabled")
        for child in main_frame.winfo_children():
            try:
                child.state(['disabled'])
            except Exception:
                pass
        menubar.entryconfig("File", state="disabled")
        menubar.entryconfig("Help", state="disabled")
        status_bar.config(text="Downloading...")
        cancel_flag['canceled'] = False
        Thread(target=download_series, daemon=True).start()

    start_btn.config(command=on_start)

    # Dynamic control enabling/disabling based on input
    def update_controls(*args):
        # Toggle episodes entry vs all checkbox
        if all_var.get():
            episodes_entry.config(state='disabled')
        else:
            episodes_entry.config(state='normal')
        if episodes_var.get().strip():
            all_check.config(state='disabled')
        else:
            all_check.config(state='normal')
        # Enable start if URL present and either all or specific episodes selected
        url_ok = bool(url_var.get().strip())
        eps_ok = bool(episodes_var.get().strip())
        if url_ok and (all_var.get() or eps_ok):
            start_btn.config(state='normal')
        else:
            start_btn.config(state='disabled')

    # Bind variable changes
    url_var.trace('w', update_controls)
    episodes_var.trace('w', update_controls)
    all_var.trace('w', update_controls)
    # Initialize control states
    update_controls()

    root.mainloop()


if __name__ == "__main__":
    main() 