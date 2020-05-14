#!/usr/bin/env python
# Windows 10 build 17063 required for native curl
from tkinter import Entry,Button,Tk,messagebox
import tkinter.font as tkFont
import tkinter.ttk
import requests
import os
import sys
import clipboard
from urllib.request import urlopen, HTTPError
import platform
import string

osys = platform.system()
real_path = os.path.dirname(os.path.realpath(__file__))

class RedditDownloader:
    def __init__(self):
        self.url = clipboard.paste()
        self.download_completed = False
        # use UA headers to prevent 429 error
        self.headers = {
                "User-Agent": "My User Agent 1.0",
                "From": "testyouremail@domain.com"
        }
        self.determine_url()
        if not self.download_completed:
            #setup UI
            self.win = Tk()
            self.win.attributes("-fullscreen", False)
            myFont = tkFont.Font(family="Mono", size=15, weight="bold")
            self.win.title("Reddit-video-downloader")
            self.win.geometry("1280x90")
            self.win.configure(background="black")

            self.urlInput = Entry(self.win)
            self.urlInput.place(x=150, y=20, height=50, width=980)

            bDownload = Button(self.win, text="Download", font=myFont, command=self.get_url_and_download)
            bDownload.place(x=20, y=20, height=50, width=120)

            bQuitter = Button(self.win, text="Exit", font=myFont, command=self.quit)
            bQuitter.place(x=1140, y=20, height=50, width=120)
            self.win.mainloop()

    def get_url_and_download(self):
        self.url = self.urlInput.get()
        self.determine_url()

    def determine_url(self):
        if isinstance(self.url, str) and (str(self.url).startswith("https://www.reddit.com") or str(self.url).startswith("https://old.reddit.com")):
            self.reddit_downloader()
        elif isinstance(self.url, str) and str(self.url).startswith("https://v.redd.it"):
            # resolve url and request with correct url
            self.resolve_vreddit_url()

    def resolve_vreddit_url(self):
        
        self.url = requests.get(self.url, headers=self.headers).url
        self.reddit_downloader()

    def open_output_dir(self):
        if osys == "Windows":
            os.system("start " + self.folder_path)
        elif osys == "Linux":
            os.system("xdg-open " + self.folder_path)
        elif osys == "Darwin":
            os.system("open " + self.folder_path)

    def reddit_downloader(self):
        try:
            self.download_completed = True
            json_url = self.url + ".json"
            data = requests.get(json_url, headers=self.headers).json()
            media_data = data[0]["data"]["children"][0]["data"]["media"]
            title = data[0]["data"]["children"][0]["data"]["title"]

            # sanitize title
            for char in string.punctuation:
                title = title.replace(char, "")

            self.video_path  = os.path.join(real_path, "Output", title)+".mp4"
            self.folder_path = os.path.join(real_path, "Output")
            if not os.path.exists(self.folder_path):
                os.makedirs(self.folder_path)

            if media_data is None:
                # might be gif, check for gif params, else no video or gif, return
                try:
                    gif_url = data[0]["data"]["children"][0]["data"]["preview"]["images"][0]["variants"]["gif"]["source"]["url"]
                    os.system("curl -o video.gif {}".format(gif_url))
                    os.system("ffmpeg -r 30 -i video.gif -movflags faststart -pix_fmt yuv420p -vf \"scale=trunc(iw/2)*2:trunc(ih/2)*2\" \"{}\"".format(self.video_path))
                    self.open_output_dir()
                except Exception as err:
                    messagebox.showerror("Error", err)
                    e_type, exc_obj, exc_tb = sys.exc_info()
                    print(err, e_type, "\nLine Number:", exc_tb.tb_lineno)
                finally:
                    return

            video_url = media_data["reddit_video"]["fallback_url"]
            audio_url = video_url.split("DASH_")[0] + "audio"
            print("Video URL: ", video_url)
            # add ffmpeg bin directory to PATH environment variable or full path to binary when ffmpeg is called with os.system()
            try:
                urlopen(audio_url)
            except HTTPError as err:
                if err.code == 403:
                    # no audio, download video only
                    os.system("curl -o video.mp4 {}".format(video_url))
                    os.system("ffmpeg -y -i video.mp4 -c:v copy -strict experimental \"{}\"".format(self.video_path))
                    self.open_output_dir()
                    return

            os.system("curl -o video.mp4 {}".format(video_url))
            os.system("curl -o audio.wav {}".format(audio_url))

            os.system("ffmpeg -y -i video.mp4 -i audio.wav -c:v copy -c:a aac -strict experimental \"{}\"".format(self.video_path))
            self.open_output_dir()
            return
        except Exception as err:
            messagebox.showerror("Error", err)
            e_type, exc_obj, exc_tb = sys.exc_info()
            print(err, e_type, "\nLine Number:", exc_tb.tb_lineno)

    def quit(self):
        self.win.destroy()
        return


if __name__ == "__main__":
    RedditDownloader()
