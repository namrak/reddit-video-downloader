# reddit-video-downloader
A simple python app with a GUI to download reddit videos on Linux and Windows

If there is already an URL in the clipboard it will use it, try to download the reddit video and open the folder that contains the output video. It will bypass the GUI.

Else: it starts the gui and you can download whatever you want from reddit.

Linux requirements: Supported applications for clipboard feature (xclip or xsel), ffmpeg bin path added to PATH variable, python3-tk

`sudo apt-get install xclip ffmpeg python3-tk`

Windows requirements: Tested only on Windows 10, curl no longer needed, ffmpeg bin path added to PATH variable

MacOS requirements: Brew allows easy install of ffmpeg/xclip (xclip also requires xquartz)

`brew cask install xquartz`

`brew install xclip ffmpeg`

MacOS issues: UI will load, buttons may not render properly, but app still works for now

```
% python redditvideos.py
DEPRECATION WARNING: The system version of Tk is deprecated and may be removed in a future release. Please don't rely on it. Set TK_SILENCE_DEPRECATION=1 to suppress this warning.
```
___

Added more detailed exception handling when debugging through terminal (also to prevent application hang)

Added error notice

Added support for videos without audio

Videos that are crossposted will yield a "'NoneType' object is not subscriptable" error

Simplified download logic

Here is a screenshot to show you the wonderful GUI that comes with it :
![screenshot](https://i.imgur.com/NOkrFTZ.png)
