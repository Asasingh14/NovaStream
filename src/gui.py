"""
GUI application for NovaStream.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import importlib.resources as resources
import multiprocessing as mp
import os
import re
from threading import Thread
from multiprocessing.dummy import Pool as ThreadPool
import shutil
import signal
from src.downloader import FFMPEG_PROCS
import logging
import json

from src.scraper import find_episode_links
from src.utils import expand_ranges
from src.downloader import download_episode


def main():
    root = tk.Tk()
    root.title("NovaStream")
    # Set window icon
    try:
        # Load bundled icon.png from package data
        icon_path = resources.files(__name__).joinpath('assets/icon.png')
        root.iconphoto(False, tk.PhotoImage(file=str(icon_path)))
    except Exception as e:  # nosec B101
        logging.warning(f"Failed to set window icon: {e}")

    # Menubar
    menubar = tk.Menu(root)
    file_menu = tk.Menu(menubar, tearoff=False)
    file_menu.add_command(label="Exit", command=root.destroy)
    menubar.add_cascade(label="File", menu=file_menu)
    help_menu = tk.Menu(menubar, tearoff=False)
    help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
        "About", "NovaStream v1.0\n© 2025 asa"))
    menubar.add_cascade(label="Help", menu=help_menu)
    root.config(menu=menubar)

    # Header with logo
    header = ttk.Frame(root, padding=(10,10))
    header.grid(row=0, column=0, sticky="EW")
    try:
        logo = tk.PhotoImage(file='icon.png')
        ttk.Label(header, image=logo).grid(row=0, column=0)
        header.image = logo
    except Exception as e:
        logging.warning("Failed to load logo image: %s", e)
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
    throttle_var = tk.IntVar(value=0)  # KB/s, 0 = unlimited
    retries_var = tk.IntVar(value=3)
    schedule_var = tk.IntVar(value=0)  # Delay start in minutes

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
    worker_scale = tk.Scale(main_frame, from_=1, to=mp.cpu_count(), variable=workers_var, orient="horizontal", resolution=1)
    worker_scale.grid(row=5, column=1, sticky="EW", pady=5)
    ttk.Label(main_frame, textvariable=workers_var).grid(row=5, column=2, sticky="W", padx=(5,0))

    # Max download rate control (Mbps)
    ttk.Label(main_frame, text="Max Rate (Mbps):").grid(row=6, column=0, sticky="E", pady=5)
    throttle_scale = tk.Scale(main_frame, from_=0, to=1000, variable=throttle_var, orient="horizontal", resolution=1)
    throttle_scale.grid(row=6, column=1, sticky="EW", pady=5)
    # Display current rate
    ttk.Label(main_frame, textvariable=throttle_var).grid(row=6, column=2, sticky="W", padx=(5,0))
    # Manual rate entry under slider
    throttle_entry = ttk.Spinbox(main_frame, from_=0, to=1000, textvariable=throttle_var, width=6)
    throttle_entry.grid(row=7, column=1, sticky="W", pady=(0,5))

    # Start delay scheduling (minutes)
    ttk.Label(main_frame, text="Start Delay (min):").grid(row=8, column=0, sticky="E", pady=5)
    schedule_scale = tk.Scale(main_frame, from_=0, to=1440, variable=schedule_var, orient="horizontal", resolution=1)
    schedule_scale.grid(row=8, column=1, sticky="EW", pady=5)
    ttk.Label(main_frame, textvariable=schedule_var).grid(row=8, column=2, sticky="W", padx=(5,0))

    # Retry attempts
    ttk.Label(main_frame, text="Retries:").grid(row=9, column=0, sticky="E", pady=5)
    ttk.Spinbox(main_frame, from_=0, to=10, textvariable=retries_var, width=5).grid(row=9, column=1, sticky="W", pady=5)

    main_frame.columnconfigure(1, weight=1)

    cancel_flag = {'canceled': False}

    # Buttons row
    btn_frame = ttk.Frame(main_frame)
    btn_frame.grid(row=10, column=0, columnspan=3, pady=(10,0))
    start_btn = ttk.Button(btn_frame, text="Start")
    start_btn.pack(side="right", padx=5)

    # Multi-drama queue with persistence
    drama_queue = []
    queue_file = 'data/drama_queue.json'
    queue_frame = ttk.Frame(root, padding=(5,5), relief="groove")
    queue_frame.grid(row=1, column=1, rowspan=10, sticky="NSW", padx=(5,0))
    ttk.Label(queue_frame, text="Drama Queue").pack()
    queue_listbox = tk.Listbox(queue_frame, width=40)
    queue_listbox.pack(fill="both", expand=True)
    btn_qf = ttk.Frame(queue_frame)
    btn_qf.pack(fill="x", pady=(5,0))

    # Load persisted queue
    try:
        with open(queue_file, 'r') as f:
            saved = json.load(f)
            for cfg in saved:
                drama_queue.append(cfg)
                queue_listbox.insert(tk.END, cfg['name'] or cfg['url'])
    except Exception as e:
        logging.warning("Failed to load drama queue from file: %s", e)
    def save_queue():
        os.makedirs(os.path.dirname(queue_file), exist_ok=True)
        with open(queue_file, 'w') as f:
            json.dump(drama_queue, f)
    def add_to_queue():
        cfg = {
            'url': url_var.get().strip(),
            'name': name_var.get().strip(),
            'output': output_var.get().strip(),
            'download_all': bool(all_var.get()),
            'episode_list': episodes_var.get().strip(),
            'workers': workers_var.get(),
            'throttle': throttle_var.get(),
            'retries': retries_var.get()
        }
        drama_queue.append(cfg)
        label = cfg['name'] or cfg['url']
        queue_listbox.insert(tk.END, label)
        save_queue()
        update_controls()
    def remove_from_queue():
        sel = queue_listbox.curselection()
        if not sel: 
            return
        i = sel[0]
        del drama_queue[i]
        queue_listbox.delete(i)
        save_queue()
        update_controls()
    def move_queue(offset):
        sel = queue_listbox.curselection()
        if not sel: 
            return
        i = sel[0]
        j = i+offset
        if 0<=j<queue_listbox.size():
            item = queue_listbox.get(i)
            cfg = drama_queue.pop(i)
            queue_listbox.delete(i)
            drama_queue.insert(j, cfg)
            queue_listbox.insert(j, item)
            queue_listbox.selection_set(j)
        save_queue()
        update_controls()
    # Double-click to load selected drama's settings
    def on_queue_double(event):
        sel = queue_listbox.curselection()
        if not sel:
            return
        cfg = drama_queue[sel[0]]
        url_var.set(cfg['url'])
        name_var.set(cfg['name'])
        output_var.set(cfg['output'])
        all_var.set(cfg['download_all'])
        episodes_var.set(cfg['episode_list'])
        workers_var.set(cfg['workers'])
        throttle_var.set(cfg['throttle'])
        retries_var.set(cfg['retries'])
    queue_listbox.config(selectmode='extended')
    queue_listbox.bind('<Double-Button-1>', on_queue_double)
    # Add start controls
    sel_frame = ttk.Frame(queue_frame)
    sel_frame.pack(fill='x', pady=(5,0))
    def start_selected():
        # Download selected dramas one by one using the UI progress popup
        for idx in list(queue_listbox.curselection()):
            cfg = drama_queue[idx]
            # mark as in progress
            queue_listbox.itemconfig(idx, fg='orange')
            # load settings into UI variables
            url_var.set(cfg['url'])
            name_var.set(cfg['name'])
            output_var.set(cfg['output'])
            all_var.set(cfg['download_all'])
            episodes_var.set(cfg['episode_list'])
            workers_var.set(cfg['workers'])
            throttle_var.set(cfg['throttle'])
            retries_var.set(cfg['retries'])
            # run download with GUI progress, passing index for post-completion coloring
            download_series(idx)
    def start_all():
        queue_listbox.select_set(0, tk.END)
        start_selected()
    ttk.Button(sel_frame, text="Start Selected", command=start_selected).pack(side='left', padx=2)
    ttk.Button(sel_frame, text="Start All", command=start_all).pack(side='left', padx=2)
    # Queue control buttons
    ttk.Button(btn_qf, text="Add", command=add_to_queue).pack(side="left", padx=2)
    ttk.Button(btn_qf, text="Remove", command=remove_from_queue).pack(side="left", padx=2)
    ttk.Button(btn_qf, text="Up", command=lambda: move_queue(-1)).pack(side="left", padx=2)
    ttk.Button(btn_qf, text="Down", command=lambda: move_queue(1)).pack(side="left", padx=2)
    # Allow clearing selection so colors remain visible
    ttk.Button(btn_qf, text="Clear Selection", command=lambda: queue_listbox.selection_clear(0, tk.END)).pack(side="left", padx=2)

    def download_series(target_index=None):
        # Threaded download with responsive UI
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
        pool_holder = {'pool': None}
        cancel_btn_popup = ttk.Button(progress_win, text="Cancel")
        cancel_btn_popup.pack(pady=(0,10))
        def on_popup_cancel():
            cancel_flag['canceled'] = True
            cancel_btn_popup.config(text="Cancelling...", state="disabled")
            stat.config(text="Cancelling...")
            try:
                prog.stop()
            except Exception as e:
                logging.warning("Cancellation failed: %s", e)
            for proc in FFMPEG_PROCS[:]:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception as e:
                    logging.warning("Cancellation failed: %s", e)
            FFMPEG_PROCS.clear()
            if pool_holder['pool']:
                pool_holder['pool'].terminate()
        cancel_btn_popup.config(command=on_popup_cancel)
        # Disable main controls
        start_btn.config(state="disabled")
        for child in main_frame.winfo_children():
            try:
                child.state(['disabled'])
            except Exception as e:
                logging.warning("Failed to re-enable widget: %s", e)
        menubar.entryconfig("File", state="disabled")
        menubar.entryconfig("Help", state="disabled")
        # Background worker thread
        def worker():
            # Gather parameters
            url = url_var.get().strip()
            name_input = name_var.get().strip()
            base_output = output_var.get().strip() or "downloads"
            download_all = bool(all_var.get())
            episode_list = episodes_var.get().strip()
            worker_count = workers_var.get()
            throttle_kbps = throttle_var.get() * 1000
            retries = retries_var.get()
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
                    total_input = simpledialog.askinteger("Total Episodes", "Could not auto-detect episodes. Enter total count:", initialvalue=1, parent=root)
                    if not total_input:
                        progress_win.after(0, progress_win.destroy)
                        progress_win.after(0, lambda: status_bar.config(text="Canceled"))
                        return
                    eps = [(n, f"{url.rstrip('/')}-episode-{n}/") for n in range(1, total_input+1)]
                elif not eps and episode_list:
                    want = expand_ranges(episode_list)
                    eps = [(n, f"{url.rstrip('/')}-episode-{n}/") for n in want]
                episodes = eps if download_all else [(n,u) for n,u in eps if n in expand_ranges(episode_list)]
            episodes.sort(key=lambda x: x[0])
            total = len(episodes)
            # Switch to determinate
            progress_win.after(0, prog.stop)
            progress_win.after(0, lambda: prog.config(mode="determinate", maximum=total, value=0))
            progress_win.after(0, lambda: stat.config(text=f"Downloading 0/{total} episodes"))
            # Start download pool
            pool = ThreadPool(worker_count)
            pool_holder['pool'] = pool
            completed = successes = failures = 0
            for result in pool.imap_unordered(download_episode, [(drama_name, num, u, drama_dir, throttle_kbps, retries) for num,u in episodes]):
                if cancel_flag['canceled']:
                    pool.terminate()
                    try:
                        shutil.rmtree(drama_dir, ignore_errors=True)
                    except Exception as e:
                        logging.warning("Cleanup error while canceling: %s", e)
                    progress_win.after(0, lambda: status_bar.config(text="Canceled (cleanup done)"))
                    progress_win.after(0, progress_win.destroy)
                    progress_win.after(0, lambda: start_btn.config(state="normal"))
                    for child in main_frame.winfo_children():
                        progress_win.after(0, lambda c=child: c.state(['!disabled']))
                    menubar.after(0, lambda: menubar.entryconfig("File", state="normal"))
                    menubar.after(0, lambda: menubar.entryconfig("Help", state="normal"))
                    cancel_flag['canceled'] = False
                    return
                completed += 1
                if result:
                    successes += 1
                else:
                    failures += 1
                progress_win.after(0, lambda c=completed, t=total: (stat.config(text=f"Downloaded {c}/{t} episodes"), prog.config(value=c)))
            pool.close()
            pool.join()
            # Finish
            progress_win.after(0, lambda: status_bar.config(text="Completed"))
            def on_finish():
                progress_win.destroy()
                msg = f"✅ Done! {successes} succeeded, {failures} failed. Files saved in:\n{drama_dir}"
                messagebox.showinfo("Done", msg)
                logging.info(f"Session complete: {successes} succeeded, {failures} failed.")
                start_btn.config(state="normal")
                for child in main_frame.winfo_children():
                    try: 
                        child.state(['!disabled'])
                    except Exception as e:
                        logging.warning("Failed to re-enable widget: %s", e)
                menubar.entryconfig("File", state="normal")
                menubar.entryconfig("Help", state="normal")
                # mark queue item green and clear selection
                if target_index is not None:
                    queue_listbox.itemconfig(target_index, fg='green')
                    queue_listbox.selection_clear(target_index)
                cancel_flag['canceled'] = False
            progress_win.after(0, on_finish)
        Thread(target=worker, daemon=True).start()

    def on_start():
        # Start concurrent downloads for all queued dramas
        for idx, cfg in enumerate(drama_queue):
            def start_cfg(i, c):
                # apply to hidden vars then launch
                url_var.set(c['url'])
                name_var.set(c['name'])
                output_var.set(c['output'])
                all_var.set(c['download_all'])
                episodes_var.set(c['episode_list'])
                workers_var.set(c['workers'])
                throttle_var.set(c['throttle'])
                retries_var.set(c['retries'])
                download_series(i)
            Thread(target=lambda i=idx, c=cfg: start_cfg(i, c), daemon=True).start()

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
        # Enable start if queue has items OR URL present with valid episodes
        url_ok = bool(url_var.get().strip())
        eps_ok = bool(episodes_var.get().strip())
        if drama_queue or (url_ok and (all_var.get() or eps_ok)):
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