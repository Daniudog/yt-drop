#!/usr/bin/env python3
"""
YT-DROP — YouTube Video Downloader
Downloads videos directly to your Downloads folder.
Requires: pip install yt-dlp
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import subprocess
import re
from pathlib import Path

# ── Try importing yt-dlp ──────────────────────────────────────────────────────
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

# ── Colors & Fonts ────────────────────────────────────────────────────────────
BG        = "#0f0f0f"
SURFACE   = "#1a1a1a"
CARD      = "#242424"
RED       = "#ff0033"
RED_DARK  = "#cc0028"
WHITE     = "#f0f0f0"
GREY      = "#888888"
GREY_DARK = "#444444"
GREEN     = "#00e676"

FONT_TITLE  = ("Georgia", 28, "bold")
FONT_LABEL  = ("Helvetica", 11)
FONT_SMALL  = ("Helvetica", 9)
FONT_MONO   = ("Courier", 9)
FONT_BTN    = ("Helvetica", 12, "bold")


def get_downloads_folder():
    """Return the OS default Downloads folder."""
    home = Path.home()
    for candidate in ["Downloads", "Download", "downloads"]:
        p = home / candidate
        if p.exists():
            return str(p)
    return str(home)


class YTDropApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YT-DROP")
        self.geometry("680x560")
        self.minsize(600, 500)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.download_path = tk.StringVar(value=get_downloads_folder())
        self.quality        = tk.StringVar(value="best")
        self.format_type    = tk.StringVar(value="mp4")
        self.url_var        = tk.StringVar()
        self.status_var     = tk.StringVar(value="Ready to download")
        self.progress_var   = tk.DoubleVar(value=0)
        self._downloading   = False

        self._build_ui()
        self._check_ytdlp()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=BG, pady=20)
        header.pack(fill="x", padx=30)

        tk.Label(header, text="▶  YT-DROP", font=FONT_TITLE,
                 bg=BG, fg=WHITE).pack(side="left")
        tk.Label(header, text="YouTube → Device", font=FONT_SMALL,
                 bg=BG, fg=RED).pack(side="left", padx=(12, 0), pady=(8, 0))

        # Separator
        tk.Frame(self, bg=RED, height=2).pack(fill="x", padx=30)

        # Main card
        card = tk.Frame(self, bg=CARD, padx=24, pady=24)
        card.pack(fill="both", expand=True, padx=30, pady=20)

        # URL input
        tk.Label(card, text="YouTube URL", font=FONT_LABEL,
                 bg=CARD, fg=GREY).pack(anchor="w")

        url_row = tk.Frame(card, bg=CARD)
        url_row.pack(fill="x", pady=(4, 14))

        self.url_entry = tk.Entry(
            url_row, textvariable=self.url_var,
            font=("Helvetica", 12), bg=SURFACE, fg=WHITE,
            insertbackground=WHITE, relief="flat",
            bd=0, highlightthickness=2,
            highlightbackground=GREY_DARK, highlightcolor=RED
        )
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=6)

        paste_btn = tk.Button(
            url_row, text="PASTE", font=FONT_SMALL,
            bg=GREY_DARK, fg=WHITE, relief="flat", bd=0,
            padx=10, cursor="hand2",
            command=self._paste_url
        )
        paste_btn.pack(side="left", padx=(6, 0), ipady=8)

        # Quality & Format row
        opts_row = tk.Frame(card, bg=CARD)
        opts_row.pack(fill="x", pady=(0, 14))

        # Quality
        q_frame = tk.Frame(opts_row, bg=CARD)
        q_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(q_frame, text="Quality", font=FONT_LABEL,
                 bg=CARD, fg=GREY).pack(anchor="w")
        quality_menu = ttk.Combobox(
            q_frame, textvariable=self.quality,
            values=["best", "1080p", "720p", "480p", "360p", "audio only"],
            state="readonly", font=FONT_LABEL
        )
        quality_menu.pack(fill="x", pady=(4, 0), ipady=4)

        # Format
        f_frame = tk.Frame(opts_row, bg=CARD)
        f_frame.pack(side="left", fill="x", expand=True)
        tk.Label(f_frame, text="Format", font=FONT_LABEL,
                 bg=CARD, fg=GREY).pack(anchor="w")
        format_menu = ttk.Combobox(
            f_frame, textvariable=self.format_type,
            values=["mp4", "mkv", "webm", "mp3", "m4a"],
            state="readonly", font=FONT_LABEL
        )
        format_menu.pack(fill="x", pady=(4, 0), ipady=4)

        # Style comboboxes
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TCombobox", fieldbackground=SURFACE,
                        background=SURFACE, foreground=WHITE,
                        selectbackground=RED, selectforeground=WHITE,
                        arrowcolor=WHITE, bordercolor=GREY_DARK)

        # Save location
        tk.Label(card, text="Save to", font=FONT_LABEL,
                 bg=CARD, fg=GREY).pack(anchor="w")

        path_row = tk.Frame(card, bg=CARD)
        path_row.pack(fill="x", pady=(4, 18))

        self.path_entry = tk.Entry(
            path_row, textvariable=self.download_path,
            font=FONT_MONO, bg=SURFACE, fg=GREEN,
            insertbackground=WHITE, relief="flat", bd=0,
            highlightthickness=2,
            highlightbackground=GREY_DARK, highlightcolor=GREEN
        )
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=6, ipadx=6)

        browse_btn = tk.Button(
            path_row, text="BROWSE", font=FONT_SMALL,
            bg=GREY_DARK, fg=WHITE, relief="flat", bd=0,
            padx=10, cursor="hand2",
            command=self._browse_folder
        )
        browse_btn.pack(side="left", padx=(6, 0), ipady=6)

        # Download button
        self.dl_btn = tk.Button(
            card, text="⬇  DOWNLOAD", font=FONT_BTN,
            bg=RED, fg=WHITE, relief="flat", bd=0,
            activebackground=RED_DARK, activeforeground=WHITE,
            cursor="hand2", pady=12,
            command=self._start_download
        )
        self.dl_btn.pack(fill="x", pady=(0, 16))

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            card, variable=self.progress_var,
            maximum=100, mode="determinate", length=400
        )
        style.configure("red.Horizontal.TProgressbar",
                        troughcolor=SURFACE, background=RED, bordercolor=CARD)
        self.progress_bar.configure(style="red.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(0, 10))

        # Status
        self.status_lbl = tk.Label(
            card, textvariable=self.status_var,
            font=FONT_SMALL, bg=CARD, fg=GREY,
            wraplength=580, justify="left"
        )
        self.status_lbl.pack(anchor="w")

        # Footer
        footer = tk.Frame(self, bg=BG, pady=6)
        footer.pack(fill="x", padx=30)
        tk.Label(footer, text="Powered by yt-dlp  •  Files saved directly to your device",
                 font=FONT_SMALL, bg=BG, fg=GREY_DARK).pack()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _check_ytdlp(self):
        if not YTDLP_AVAILABLE:
            self.status_var.set("⚠  yt-dlp not found. Click Download — it will auto-install.")
            self.status_lbl.configure(fg="#ffaa00")

    def _paste_url(self):
        try:
            text = self.clipboard_get()
            self.url_var.set(text.strip())
        except Exception:
            pass

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path.get())
        if folder:
            self.download_path.set(folder)

    def _set_status(self, msg, color=GREY):
        self.status_var.set(msg)
        self.status_lbl.configure(fg=color)

    def _set_progress(self, pct):
        self.progress_var.set(pct)

    # ── Download Logic ────────────────────────────────────────────────────────

    def _start_download(self):
        if self._downloading:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please paste a YouTube URL first.")
            return

        if "youtube.com" not in url and "youtu.be" not in url:
            messagebox.showwarning("Invalid URL", "Please enter a valid YouTube URL.")
            return

        self._downloading = True
        self.dl_btn.configure(state="disabled", text="Downloading…", bg=GREY_DARK)
        self._set_progress(0)
        self._set_status("Starting download…", WHITE)

        thread = threading.Thread(target=self._do_download, args=(url,), daemon=True)
        thread.start()

    def _do_download(self, url):
        # Auto-install yt-dlp if missing
        if not YTDLP_AVAILABLE:
            self._set_status("Installing yt-dlp…", "#ffaa00")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "yt-dlp", "-q"]
                )
                import importlib
                import yt_dlp as _yt
            except Exception as e:
                self.after(0, self._download_failed, f"Could not install yt-dlp: {e}")
                return

        import yt_dlp

        quality   = self.quality.get()
        fmt       = self.format_type.get()
        save_path = self.download_path.get()

        # Build format selector
        if quality == "audio only" or fmt in ("mp3", "m4a"):
            ydl_format = "bestaudio/best"
            postprocessors = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt if fmt in ("mp3", "m4a") else "mp3",
                "preferredquality": "192",
            }]
        elif quality == "best":
            ydl_format = f"bestvideo[ext={fmt}]+bestaudio/best[ext={fmt}]/best"
            postprocessors = []
        else:
            height = quality.replace("p", "")
            ydl_format = (
                f"bestvideo[height<={height}][ext={fmt}]+bestaudio/best"
                f"/bestvideo[height<={height}]+bestaudio/best"
            )
            postprocessors = []

        ydl_opts = {
            "format": ydl_format,
            "outtmpl": os.path.join(save_path, "%(title)s.%(ext)s"),
            "postprocessors": postprocessors,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": fmt if fmt not in ("mp3", "m4a") else None,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Video")
                self.after(0, self._set_status, f'Downloading: "{title}"', WHITE)
                ydl.download([url])
            self.after(0, self._download_done, title, save_path)
        except Exception as e:
            self.after(0, self._download_failed, str(e))

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            raw = d.get("_percent_str", "0%").strip()
            pct_str = re.sub(r"\x1b\[[0-9;]*m", "", raw)  # strip ANSI
            try:
                pct = float(pct_str.replace("%", ""))
                self.after(0, self._set_progress, pct)
                speed = d.get("_speed_str", "").strip()
                eta   = d.get("_eta_str", "").strip()
                self.after(0, self._set_status,
                           f"Downloading… {pct_str}  |  {speed}  |  ETA {eta}", WHITE)
            except ValueError:
                pass
        elif d["status"] == "finished":
            self.after(0, self._set_progress, 95)
            self.after(0, self._set_status, "Processing…", WHITE)

    def _download_done(self, title, save_path):
        self._downloading = False
        self._set_progress(100)
        self._set_status(f'✓  Saved "{title}" → {save_path}', GREEN)
        self.dl_btn.configure(state="normal", text="⬇  DOWNLOAD", bg=RED)
        self.url_var.set("")

    def _download_failed(self, error):
        self._downloading = False
        self._set_progress(0)
        short_err = error[:120] + "…" if len(error) > 120 else error
        self._set_status(f"✗  Error: {short_err}", "#ff4444")
        self.dl_btn.configure(state="normal", text="⬇  DOWNLOAD", bg=RED)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = YTDropApp()
    app.mainloop()