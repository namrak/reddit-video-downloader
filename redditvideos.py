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
            
            # sanitize title for file path
            for char in string.punctuation:
                title = title.replace(char, "")
            # account for titles that are too long
            if len(title) > 50:
                title = title[0:49]

            self.folder_path = os.path.join(real_path, "Output")
            self.video_path  = os.path.join(self.folder_path, title)+".mp4"
            self.gif_path = os.path.join(self.folder_path, title)+".gif"
            
            if not os.path.exists(self.folder_path):
                os.makedirs(self.folder_path)

            if media_data is None:
                # might be gif, check for gif params, else no video or gif, return
                try:
                    gif_url = data[0]["data"]["children"][0]["data"]["preview"]["images"][0]["variants"]["gif"]["source"]["url"]
                    gif_request = requests.get(gif_url, headers=self.headers)
                    with open(self.gif_path, "wb") as output_gif:
                        output_gif.write(gif_request.content)
                    self.open_output_dir()
                except Exception as err:
                    messagebox.showerror("Error", "No video or gif")
                    e_type, exc_obj, exc_tb = sys.exc_info()
                    print(err, e_type, "\nLine Number:", exc_tb.tb_lineno)
                finally:
                    return

            dash_url = media_data["reddit_video"]["dash_url"]
            dash_url = dash_url.split("?")[0]

            os.system("ffmpeg -y -i {} -c copy \"{}\"".format(dash_url, self.video_path))
            self.open_output_dir()
        except Exception as err:
            messagebox.showerror("Error", err)
            e_type, exc_obj, exc_tb = sys.exc_info()
            print(err, e_type, "\nLine Number:", exc_tb.tb_lineno)

    def quit(self):
        self.win.destroy()
        return


if __name__ == "__main__":
    RedditDownloader()
