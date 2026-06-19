"""Tkinter GUI for NovaStream."""

import importlib.resources as resources
import json
import logging
import multiprocessing as mp
import os
import queue
import re
import tkinter as tk
from multiprocessing.dummy import Pool as ThreadPool
from threading import Event, Thread
from tkinter import filedialog, messagebox, simpledialog, ttk

from src.downloader import DownloadControl, download_episode, sanitize_path_component
from src.scraper import find_episode_links
from src.utils import expand_ranges


def _queue_file_path():
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "NovaStream", "drama_queue.json")
    return os.path.join(os.path.expanduser("~"), ".novastream", "drama_queue.json")


def main():
    root = tk.Tk()
    root.title("NovaStream")

    try:
        icon_path = resources.files("src").joinpath("assets/icon.png")
        app_icon = tk.PhotoImage(file=str(icon_path))
        root.iconphoto(False, app_icon)
    except (AttributeError, FileNotFoundError, tk.TclError) as e:
        logging.warning("Failed to set window icon: %s", e)

    menubar = tk.Menu(root)
    file_menu = tk.Menu(menubar, tearoff=False)
    file_menu.add_command(label="Exit", command=root.destroy)
    menubar.add_cascade(label="File", menu=file_menu)
    help_menu = tk.Menu(menubar, tearoff=False)
    help_menu.add_command(
        label="About",
        command=lambda: messagebox.showinfo("About", "NovaStream v1.0\n© 2026 asa"),
    )
    menubar.add_cascade(label="Help", menu=help_menu)
    root.config(menu=menubar)

    header = ttk.Frame(root, padding=(10, 10))
    header.grid(row=0, column=0, sticky="EW")
    try:
        logo_path = resources.files("src").joinpath("assets/icon.png")
        logo = tk.PhotoImage(file=str(logo_path))
        ttk.Label(header, image=logo).grid(row=0, column=0)
        header.image = logo
    except (AttributeError, FileNotFoundError, tk.TclError) as e:
        logging.warning("Failed to load logo image: %s", e)
        ttk.Label(header, text="NovaStream", font=("Segoe UI", 16)).grid(row=0, column=0)

    main_frame = ttk.Frame(root, padding=(20, 10))
    main_frame.grid(row=1, column=0, sticky="NSEW")
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)

    status_bar = ttk.Label(root, text="Ready", relief="sunken", anchor="w")
    status_bar.grid(row=2, column=0, columnspan=2, sticky="EW")

    max_workers = max(1, min(16, mp.cpu_count()))
    url_var = tk.StringVar()
    name_var = tk.StringVar()
    output_var = tk.StringVar(value="downloads")
    all_var = tk.BooleanVar(value=True)
    episodes_var = tk.StringVar()
    workers_var = tk.IntVar(value=min(4, max_workers))
    retries_var = tk.IntVar(value=3)
    schedule_var = tk.IntVar(value=0)

    ttk.Label(main_frame, text="Drama URL:").grid(row=0, column=0, sticky="E", pady=5)
    url_entry = ttk.Entry(main_frame, textvariable=url_var, width=40)
    url_entry.grid(row=0, column=1, columnspan=2, sticky="EW", pady=5)

    ttk.Label(main_frame, text="Drama Name:").grid(row=1, column=0, sticky="E", pady=5)
    name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40)
    name_entry.grid(row=1, column=1, columnspan=2, sticky="EW", pady=5)

    ttk.Label(main_frame, text="Output Folder:").grid(row=2, column=0, sticky="E", pady=5)
    output_entry = ttk.Entry(main_frame, textvariable=output_var, width=30)
    output_entry.grid(row=2, column=1, sticky="EW", pady=5)

    def browse_output():
        selected = filedialog.askdirectory()
        if selected:
            output_var.set(selected)

    browse_btn = ttk.Button(main_frame, text="Browse...", command=browse_output)
    browse_btn.grid(row=2, column=2, sticky="W", padx=5)

    all_check = ttk.Checkbutton(main_frame, text="Download ALL episodes", variable=all_var)
    all_check.grid(row=3, column=0, columnspan=3, sticky="W", pady=5)

    ttk.Label(main_frame, text="Episodes (e.g. 1,3-5):").grid(row=4, column=0, sticky="E", pady=5)
    episodes_entry = ttk.Entry(main_frame, textvariable=episodes_var, width=40)
    episodes_entry.grid(row=4, column=1, columnspan=2, sticky="EW", pady=5)

    ttk.Label(main_frame, text="Workers:").grid(row=5, column=0, sticky="E", pady=5)
    worker_scale = tk.Scale(
        main_frame,
        from_=1,
        to=max_workers,
        variable=workers_var,
        orient="horizontal",
        resolution=1,
    )
    worker_scale.grid(row=5, column=1, sticky="EW", pady=5)
    ttk.Label(main_frame, textvariable=workers_var).grid(row=5, column=2, sticky="W", padx=(5, 0))

    ttk.Label(main_frame, text="Start Delay (min):").grid(row=6, column=0, sticky="E", pady=5)
    schedule_scale = tk.Scale(
        main_frame,
        from_=0,
        to=1440,
        variable=schedule_var,
        orient="horizontal",
        resolution=1,
    )
    schedule_scale.grid(row=6, column=1, sticky="EW", pady=5)
    ttk.Label(main_frame, textvariable=schedule_var).grid(row=6, column=2, sticky="W", padx=(5, 0))

    ttk.Label(main_frame, text="Retries:").grid(row=7, column=0, sticky="E", pady=5)
    retries_spin = ttk.Spinbox(main_frame, from_=0, to=10, textvariable=retries_var, width=5)
    retries_spin.grid(row=7, column=1, sticky="W", pady=5)
    main_frame.columnconfigure(1, weight=1)

    btn_frame = ttk.Frame(main_frame)
    btn_frame.grid(row=8, column=0, columnspan=3, pady=(10, 0))
    start_btn = ttk.Button(btn_frame, text="Start")
    start_btn.pack(side="right", padx=5)

    queue_frame = ttk.Frame(root, padding=(5, 5), relief="groove")
    queue_frame.grid(row=1, column=1, sticky="NSEW", padx=(5, 0))
    root.grid_columnconfigure(1, weight=1)
    ttk.Label(queue_frame, text="Drama Queue").pack()
    queue_listbox = tk.Listbox(queue_frame, width=40, selectmode="extended")
    queue_listbox.pack(fill="both", expand=True)
    queue_start_frame = ttk.Frame(queue_frame)
    queue_start_frame.pack(fill="x", pady=(5, 0))
    queue_edit_frame = ttk.Frame(queue_frame)
    queue_edit_frame.pack(fill="x", pady=(5, 0))

    ui_events = queue.Queue()

    def post_ui(callback):
        ui_events.put(callback)

    def process_ui_events():
        while True:
            try:
                callback = ui_events.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                logging.exception("GUI update failed")
        root.after(50, process_ui_events)

    root.after(50, process_ui_events)

    drama_queue = []
    queue_file = _queue_file_path()
    legacy_queue_file = os.path.join("data", "drama_queue.json")
    job_state = {"running": False, "queue_active": False}
    queue_buttons = []

    def config_from_form():
        return {
            "url": url_var.get().strip(),
            "name": name_var.get().strip(),
            "output": output_var.get().strip() or "downloads",
            "download_all": bool(all_var.get()),
            "episode_list": episodes_var.get().strip(),
            "workers": max(1, min(max_workers, workers_var.get())),
            "retries": max(0, retries_var.get()),
            "delay": max(0, schedule_var.get()),
        }

    def validate_config(config):
        if not re.match(r"^https?://", config.get("url", ""), re.IGNORECASE):
            return "Enter a valid http:// or https:// drama URL."
        if not config.get("download_all"):
            selection = config.get("episode_list", "")
            if not selection:
                return "Enter an episode selection or enable Download ALL episodes."
            try:
                expand_ranges(selection)
            except (TypeError, ValueError):
                return "Episode selection must look like 1,3-5."
        return None

    def save_queue():
        try:
            os.makedirs(os.path.dirname(queue_file), exist_ok=True)
            with open(queue_file, "w", encoding="utf-8") as queue_handle:
                json.dump(drama_queue, queue_handle, indent=2)
        except OSError as e:
            logging.error("Failed to save drama queue: %s", e)
            messagebox.showerror("Queue Error", f"Could not save the queue:\n{e}")

    def load_queue():
        load_path = queue_file if os.path.exists(queue_file) else legacy_queue_file
        try:
            with open(load_path, "r", encoding="utf-8") as queue_handle:
                saved = json.load(queue_handle)
        except FileNotFoundError:
            return
        except (OSError, ValueError, TypeError) as e:
            logging.warning("Failed to load drama queue: %s", e)
            return
        for config in saved:
            if isinstance(config, dict) and config.get("url"):
                drama_queue.append(config)
                queue_listbox.insert(tk.END, config.get("name") or config["url"])

    def add_to_queue():
        config = config_from_form()
        error = validate_config(config)
        if error:
            messagebox.showerror("Invalid Download", error)
            return
        drama_queue.append(config)
        queue_listbox.insert(tk.END, config["name"] or config["url"])
        save_queue()
        update_controls()

    def remove_from_queue():
        indices = list(queue_listbox.curselection())
        for index in reversed(indices):
            del drama_queue[index]
            queue_listbox.delete(index)
        if indices:
            save_queue()
            update_controls()

    def move_queue(offset):
        selection = queue_listbox.curselection()
        if len(selection) != 1:
            return
        index = selection[0]
        destination = index + offset
        if not 0 <= destination < len(drama_queue):
            return
        config = drama_queue.pop(index)
        label = queue_listbox.get(index)
        queue_listbox.delete(index)
        drama_queue.insert(destination, config)
        queue_listbox.insert(destination, label)
        queue_listbox.selection_set(destination)
        save_queue()

    def load_selected_config(_event=None):
        selection = queue_listbox.curselection()
        if not selection:
            return
        config = drama_queue[selection[0]]
        url_var.set(config.get("url", ""))
        name_var.set(config.get("name", ""))
        output_var.set(config.get("output", "downloads"))
        all_var.set(bool(config.get("download_all", True)))
        episodes_var.set(config.get("episode_list", ""))
        workers_var.set(max(1, min(max_workers, int(config.get("workers", 4)))))
        retries_var.set(max(0, int(config.get("retries", 3))))
        schedule_var.set(max(0, int(config.get("delay", 0))))

    queue_listbox.bind("<Double-Button-1>", load_selected_config)

    form_widgets = [
        url_entry,
        name_entry,
        output_entry,
        browse_btn,
        all_check,
        episodes_entry,
        worker_scale,
        schedule_scale,
        retries_spin,
        start_btn,
    ]

    def set_controls_enabled(enabled):
        for widget in form_widgets:
            try:
                widget.config(state="normal" if enabled else "disabled")
            except tk.TclError:
                pass
        for widget in queue_buttons:
            widget.config(state="normal" if enabled else "disabled")
        menubar.entryconfig("File", state="normal" if enabled else "disabled")
        menubar.entryconfig("Help", state="normal" if enabled else "disabled")
        if enabled:
            update_controls()

    def ask_total_episodes():
        answer = {"value": None}
        answered = Event()

        def prompt():
            answer["value"] = simpledialog.askinteger(
                "Total Episodes",
                "Could not auto-detect episodes. Enter total count:",
                initialvalue=1,
                minvalue=1,
                parent=root,
            )
            answered.set()

        post_ui(prompt)
        answered.wait()
        return answer["value"]

    def download_series(config, target_index=None, on_complete=None):
        config = dict(config)
        error = validate_config(config)
        if error:
            messagebox.showerror("Invalid Download", error)
            if target_index is not None:
                queue_listbox.itemconfig(target_index, fg="red")
            if on_complete:
                on_complete(False, False)
            return
        if job_state["running"]:
            messagebox.showinfo("Download Running", "Wait for the current download to finish first.")
            return

        job_state["running"] = True
        progress_win = tk.Toplevel(root)
        progress_win.title("Downloading...")
        progress_win.resizable(False, False)
        ttk.Label(progress_win, text="Starting...").pack(padx=10, pady=(10, 0))
        progress = ttk.Progressbar(progress_win, orient="horizontal", length=300, mode="indeterminate")
        progress.pack(padx=10, pady=10)
        progress.start()
        progress_status = ttk.Label(progress_win, text="")
        progress_status.pack(padx=10, pady=(0, 10))
        progress_win.transient(root)
        progress_win.grab_set()

        pool_holder = {"pool": None}
        control = DownloadControl()
        finished = {"value": False}
        cancel_button = ttk.Button(progress_win, text="Cancel")
        cancel_button.pack(pady=(0, 10))

        def request_cancel():
            control.cancel()
            cancel_button.config(text="Cancelling...", state="disabled")
            progress_status.config(text="Cancelling; completed files will be kept...")
            pool = pool_holder["pool"]
            if pool:
                pool.terminate()

        cancel_button.config(command=request_cancel)
        progress_win.protocol("WM_DELETE_WINDOW", request_cancel)
        set_controls_enabled(False)

        def finish(successes=0, failures=0, cancelled=False, error_message=None, drama_dir=None):
            if finished["value"]:
                return
            finished["value"] = True
            job_state["running"] = False
            try:
                progress_win.grab_release()
                progress_win.destroy()
            except tk.TclError:
                pass

            successful = not cancelled and not error_message and failures == 0
            if target_index is not None:
                color = "green" if successful else ("orange" if cancelled else "red")
                queue_listbox.itemconfig(target_index, fg=color)
                queue_listbox.selection_clear(target_index)

            if cancelled:
                status_bar.config(text="Canceled; completed files kept")
            elif error_message:
                status_bar.config(text="Failed")
                messagebox.showerror("Download Error", error_message)
            else:
                status_bar.config(text="Completed")
                if target_index is None:
                    messagebox.showinfo(
                        "Done",
                        f"✅ Done! {successes} succeeded, {failures} failed. Files saved in:\n{drama_dir}",
                    )

            if on_complete:
                on_complete(successful, cancelled)
            elif not job_state["queue_active"]:
                set_controls_enabled(True)

        def worker():
            pool = None
            try:
                url = config["url"]
                raw_name = config.get("name") or re.sub(
                    r"[^0-9a-zA-Z]+",
                    "_",
                    url.rstrip("/").split("/")[-1],
                )
                drama_name = sanitize_path_component(raw_name, fallback="download").replace(" ", "_")
                drama_dir = os.path.join(config.get("output") or "downloads", drama_name)
                os.makedirs(drama_dir, exist_ok=True)

                delay_seconds = max(0, int(config.get("delay", 0))) * 60
                if delay_seconds:
                    post_ui(
                        lambda: progress_status.config(
                            text=f"Scheduled to start in {delay_seconds // 60} minute(s)"
                        )
                    )
                    if control.cancelled.wait(delay_seconds):
                        post_ui(lambda: finish(cancelled=True, drama_dir=drama_dir))
                        return

                match = re.search(r"(?:episode|ep)[-_/]?(\d+)", url, re.IGNORECASE)
                if match:
                    episodes = [(int(match.group(1)), url)]
                else:
                    episodes_found = find_episode_links(url)
                    if not episodes_found and config.get("download_all"):
                        total = ask_total_episodes()
                        if not total:
                            post_ui(lambda: finish(cancelled=True, drama_dir=drama_dir))
                            return
                        episodes_found = [
                            (number, f"{url.rstrip('/')}-episode-{number}/")
                            for number in range(1, total + 1)
                        ]
                    elif not episodes_found and config.get("episode_list"):
                        episodes_found = [
                            (number, f"{url.rstrip('/')}-episode-{number}/")
                            for number in expand_ranges(config["episode_list"])
                        ]
                    if config.get("download_all"):
                        episodes = episodes_found
                    else:
                        requested = set(expand_ranges(config["episode_list"]))
                        episodes = [item for item in episodes_found if item[0] in requested]

                episodes.sort(key=lambda item: item[0])
                if not episodes:
                    post_ui(lambda: finish(error_message="No matching episodes were found.", drama_dir=drama_dir))
                    return

                total = len(episodes)
                post_ui(progress.stop)
                post_ui(lambda: progress.config(mode="determinate", maximum=total, value=0))
                post_ui(lambda: progress_status.config(text=f"Downloading 0/{total} episodes"))

                workers = max(1, min(max_workers, int(config.get("workers", 4))))
                retries = max(0, int(config.get("retries", 3)))
                pool = ThreadPool(workers)
                pool_holder["pool"] = pool
                completed = successes = failures = 0
                arguments = [
                    (drama_name, number, episode_url, drama_dir, 0, retries, control)
                    for number, episode_url in episodes
                ]
                for result in pool.imap_unordered(download_episode, arguments):
                    if control.cancelled.is_set():
                        break
                    completed += 1
                    successes += int(bool(result))
                    failures += int(not result)
                    post_ui(
                        lambda done=completed: (
                            progress_status.config(text=f"Downloaded {done}/{total} episodes"),
                            progress.config(value=done),
                        )
                    )

                if control.cancelled.is_set():
                    post_ui(lambda: finish(successes, failures, True, drama_dir=drama_dir))
                else:
                    logging.info("Session complete: %s succeeded, %s failed", successes, failures)
                    post_ui(lambda: finish(successes, failures, drama_dir=drama_dir))
            except Exception as e:
                if control.cancelled.is_set():
                    post_ui(lambda: finish(cancelled=True))
                else:
                    logging.exception("Download job failed")
                    post_ui(lambda message=str(e): finish(error_message=message))
            finally:
                if pool:
                    if control.cancelled.is_set():
                        pool.terminate()
                    else:
                        pool.close()
                    pool.join()

        Thread(target=worker, daemon=True).start()

    def run_queue(indices):
        if job_state["running"] or job_state["queue_active"]:
            messagebox.showinfo("Download Running", "Wait for the current download to finish first.")
            return
        jobs = [(index, dict(drama_queue[index])) for index in indices if 0 <= index < len(drama_queue)]
        if not jobs:
            return

        job_state["queue_active"] = True
        results = {"successes": 0, "failures": 0}
        set_controls_enabled(False)

        def start_next(position):
            if position >= len(jobs):
                job_state["queue_active"] = False
                set_controls_enabled(True)
                messagebox.showinfo(
                    "Queue Complete",
                    f"{results['successes']} drama(s) completed; {results['failures']} failed.",
                )
                return

            index, config = jobs[position]
            queue_listbox.itemconfig(index, fg="orange")

            def completed(successful, cancelled):
                if cancelled:
                    job_state["queue_active"] = False
                    set_controls_enabled(True)
                    return
                results["successes" if successful else "failures"] += 1
                start_next(position + 1)

            download_series(config, target_index=index, on_complete=completed)

        start_next(0)

    def start_current():
        config = config_from_form()
        error = validate_config(config)
        if error:
            messagebox.showerror("Invalid Download", error)
            return
        download_series(config)

    def start_selected():
        selection = list(queue_listbox.curselection())
        if not selection:
            messagebox.showinfo("Drama Queue", "Select at least one drama to start.")
            return
        run_queue(selection)

    def start_all():
        run_queue(list(range(len(drama_queue))))

    start_btn.config(command=start_current)
    start_selected_btn = ttk.Button(queue_start_frame, text="Start Selected", command=start_selected)
    start_selected_btn.pack(side="left", padx=2)
    start_all_btn = ttk.Button(queue_start_frame, text="Start All", command=start_all)
    start_all_btn.pack(side="left", padx=2)
    add_btn = ttk.Button(queue_edit_frame, text="Add", command=add_to_queue)
    add_btn.pack(side="left", padx=2)
    remove_btn = ttk.Button(queue_edit_frame, text="Remove", command=remove_from_queue)
    remove_btn.pack(side="left", padx=2)
    up_btn = ttk.Button(queue_edit_frame, text="Up", command=lambda: move_queue(-1))
    up_btn.pack(side="left", padx=2)
    down_btn = ttk.Button(queue_edit_frame, text="Down", command=lambda: move_queue(1))
    down_btn.pack(side="left", padx=2)
    clear_btn = ttk.Button(
        queue_edit_frame,
        text="Clear Selection",
        command=lambda: queue_listbox.selection_clear(0, tk.END),
    )
    clear_btn.pack(side="left", padx=2)
    queue_buttons.extend([start_selected_btn, start_all_btn, add_btn, remove_btn, up_btn, down_btn, clear_btn])

    def update_controls(*_args):
        episodes_entry.config(state="disabled" if all_var.get() else "normal")
        all_check.config(state="disabled" if episodes_var.get().strip() else "normal")
        form_ready = bool(url_var.get().strip()) and (all_var.get() or bool(episodes_var.get().strip()))
        start_btn.config(state="normal" if form_ready and not job_state["running"] else "disabled")
        start_selected_btn.config(state="normal" if drama_queue and not job_state["running"] else "disabled")
        start_all_btn.config(state="normal" if drama_queue and not job_state["running"] else "disabled")

    url_var.trace_add("write", update_controls)
    episodes_var.trace_add("write", update_controls)
    all_var.trace_add("write", update_controls)
    load_queue()
    update_controls()
    root.mainloop()


if __name__ == "__main__":
    main()
