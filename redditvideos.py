#!/usr/bin/env python
import sys
import os
import platform
import re
import subprocess
import shutil
import threading
import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkFont
import requests
import clipboard
from pathlib import Path

class RedditDownloader:
    """Handles the downloading and processing of Reddit videos and GIFs."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "From": "reddit-video-downloader@example.com"
        }
        self.output_dir = Path(__file__).parent / "Output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_title(self, title):
        """Sanitizes the post title to be used as a filename."""
        # Remove characters that are not letters, numbers, spaces, or hyphens
        title = re.sub(r'[^\w\s-]', '', title).strip()
        # Replace multiple spaces with a single space
        title = re.sub(r'\s+', ' ', title)
        # Limit length to 50 characters to avoid path issues
        return title[:50]

    def get_json_data(self, url):
        """Fetches and parses JSON data for a Reddit post."""
        try:
            # Strip query params and append .json
            clean_url = url.split('?')[0].rstrip('/') + ".json"
            response = requests.get(clean_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch Reddit data: {e}")

    def resolve_vreddit_url(self, url):
        """Resolves v.redd.it short URLs to their full Reddit post URLs."""
        try:
            response = requests.get(url, headers=self.headers, allow_redirects=True, timeout=10)
            return response.url
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to resolve v.redd.it URL: {e}")

    def download(self, url, status_callback=None):
        """Main download logic. Returns the path to the downloaded file."""
        if not shutil.which("ffmpeg"):
            raise Exception("ffmpeg not found in PATH. Please install it to download videos.")

        if "v.redd.it" in url:
            if status_callback: status_callback("Resolving short URL...")
            url = self.resolve_vreddit_url(url)

        if "reddit.com" not in url:
            raise Exception("Invalid Reddit URL. Please provide a link to a Reddit post.")

        if status_callback: status_callback("Fetching metadata...")
        data = self.get_json_data(url)

        try:
            # Reddit API returns a list of two objects for posts
            post_data = data[0]["data"]["children"][0]["data"]
            title = self.sanitize_title(post_data.get("title", "reddit_video"))
            media = post_data.get("media")
            
            # Check for GIF variants first if no standard media object exists
            if not media:
                try:
                    # Attempt to find a GIF source
                    gif_url = post_data["preview"]["images"][0]["variants"]["gif"]["source"]["url"]
                    # Reddit HTML-escapes & in URLs in the JSON
                    gif_url = gif_url.replace("&amp;", "&")
                    
                    if status_callback: status_callback("Downloading GIF...")
                    gif_path = self.output_dir / f"{title}.gif"
                    
                    response = requests.get(gif_url, headers=self.headers, stream=True)
                    response.raise_for_status()
                    with open(gif_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    return gif_path
                except (KeyError, IndexError):
                    raise Exception("No video or GIF found in this post.")

            video_data = media.get("reddit_video")
            if not video_data:
                raise Exception("Could not find video data in the media object.")

            # Prefer DASH URL for best quality and audio sync
            dash_url = video_data.get("dash_url", "").split("?")[0]
            if not dash_url:
                # Fallback to direct video URL
                dash_url = video_data.get("fallback_url", "").split("?")[0]
            
            if not dash_url:
                raise Exception("Could not find video stream URL.")

            video_path = self.output_dir / f"{title}.mp4"
            
            if status_callback: status_callback("Downloading video (ffmpeg)...")
            
            # Use ffmpeg to process the DASH stream. 
            # It handles audio/video muxing automatically from the manifest.
            cmd = [
                "ffmpeg", "-y", "-i", dash_url, 
                "-c", "copy", "-movflags", "faststart", str(video_path)
            ]
            
            # Set creationflags to hide console window on Windows
            creation_flags = 0
            if platform.system() == "Windows":
                creation_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                creationflags=creation_flags
            )
            
            if result.returncode != 0:
                # If ffmpeg failed, it might be due to DASH issues. Try fallback_url if we haven't already.
                fallback_url = video_data.get("fallback_url", "").split("?")[0]
                if dash_url != fallback_url:
                     if status_callback: status_callback("DASH failed, trying fallback...")
                     cmd[3] = fallback_url
                     result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creation_flags)
                
                if result.returncode != 0:
                    raise Exception(f"ffmpeg error: {result.stderr}")

            return video_path

        except (KeyError, IndexError, TypeError) as e:
            raise Exception(f"Error parsing Reddit response: {e}")

    def open_folder(self, path):
        """Opens the folder containing the downloaded file in the system file explorer."""
        folder = Path(path).parent
        osys = platform.system()
        try:
            if osys == "Windows":
                os.startfile(folder)
            elif osys == "Darwin":
                subprocess.run(["open", str(folder)])
            else:  # Linux
                subprocess.run(["xdg-open", str(folder)])
        except Exception:
            pass 

class RedditDownloaderApp:
    """The Tkinter GUI application."""
    
    def __init__(self, root):
        self.root = root
        self.downloader = RedditDownloader()
        self.setup_ui()
        
        # Check clipboard on start after a short delay to allow UI to render
        self.root.after(500, self.check_clipboard)

    def setup_ui(self):
        self.root.title("Reddit Video Downloader")
        self.root.geometry("700x200")
        self.root.resizable(False, False)
        self.root.configure(background="#1a1a1b") 

        font_style = tkFont.Font(family="Helvetica", size=11, weight="bold")
        
        # Main Frame
        main_frame = tk.Frame(self.root, bg="#1a1a1b", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # URL Label
        tk.Label(main_frame, text="Reddit Post URL:", bg="#1a1a1b", fg="white", font=("Helvetica", 10)).pack(anchor="w")

        # URL Entry
        self.url_var = tk.StringVar()
        self.entry = tk.Entry(main_frame, textvariable=self.url_var, font=("Helvetica", 11), bg="#272729", fg="white", insertbackground="white", borderwidth=0)
        self.entry.pack(fill=tk.X, pady=(5, 15))
        self.entry.focus_set()

        # Button Frame
        btn_frame = tk.Frame(main_frame, bg="#1a1a1b")
        btn_frame.pack(fill=tk.X)

        self.download_btn = tk.Button(btn_frame, text="Download", font=font_style, bg="#ff4500", fg="white", activebackground="#ff5a1f", activeforeground="white", relief=tk.FLAT, command=self.start_download, width=15)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_btn = tk.Button(btn_frame, text="Clear", font=font_style, bg="#333333", fg="white", activebackground="#444444", activeforeground="white", relief=tk.FLAT, command=lambda: self.url_var.set(""), width=10)
        self.clear_btn.pack(side=tk.LEFT)

        self.exit_btn = tk.Button(btn_frame, text="Exit", font=font_style, bg="#333333", fg="white", activebackground="#444444", activeforeground="white", relief=tk.FLAT, command=self.root.quit, width=10)
        self.exit_btn.pack(side=tk.RIGHT)

        # Status Label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(main_frame, textvariable=self.status_var, bg="#1a1a1b", fg="#818384", font=("Helvetica", 9))
        self.status_label.pack(side=tk.BOTTOM, pady=(10, 0))

    def check_clipboard(self):
        """Checks the clipboard for a Reddit URL on startup."""
        try:
            content = clipboard.paste()
            if content and isinstance(content, str):
                content = content.strip()
                if "reddit.com" in content or "v.redd.it" in content:
                    self.url_var.set(content)
                    self.update_status("URL detected in clipboard. Starting auto-download...")
                    self.start_download()
        except Exception:
            pass

    def update_status(self, text):
        """Updates the status label text."""
        self.status_var.set(text)
        self.root.update_idletasks()

    def start_download(self):
        """Starts the download process in a separate thread."""
        url = self.url_var.get().strip()
        if not url:
            return

        self.download_btn.config(state=tk.DISABLED)
        self.update_status("Starting...")
        
        threading.Thread(target=self.run_download, args=(url,), daemon=True).start()

    def run_download(self, url):
        """Background task for downloading."""
        try:
            path = self.downloader.download(url, status_callback=self.update_status)
            self.update_status(f"Download complete!")
            messagebox.showinfo("Success", f"File saved to:\n{path}")
            self.downloader.open_folder(path)
        except Exception as e:
            self.update_status("Error occurred.")
            messagebox.showerror("Error", str(e))
        finally:
            self.download_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Reddit Video Downloader")
    parser.add_argument("url", nargs="?", help="URL of the Reddit post to download")
    args = parser.parse_args()

    downloader = RedditDownloader()

    # Try to initialize GUI
    root = None
    try:
        root = tk.Tk()
        app = RedditDownloaderApp(root)

        # If a URL was passed via CLI, override clipboard/entry
        if args.url:
            app.url_var.set(args.url)
            app.start_download()

        root.mainloop()
    except tk.TclError:
        # Headless mode
        print("Headless environment detected. Operating in CLI mode.")

        target_url = args.url
        if not target_url:
            try:
                content = clipboard.paste()
                if content and isinstance(content, str) and ("reddit.com" in content or "v.redd.it" in content):
                    target_url = content.strip()
                    print(f"Detected URL in clipboard: {target_url}")
            except Exception:
                pass

        if target_url:
            try:
                print("Starting download...")
                # In headless mode, we don't want to open the folder
                path = downloader.download(target_url, status_callback=print)
                print(f"\nSuccess! File saved to: {path}")
            except Exception as e:
                print(f"\nError: {e}")
                sys.exit(1)
        else:
            print("Error: No URL provided via argument and no Reddit URL found in clipboard.")
            parser.print_help()
            sys.exit(1)

