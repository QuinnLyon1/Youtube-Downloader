# YouTube Downloader

A Python desktop GUI application for downloading and trimming YouTube videos with custom start/end times.

## 🚀 Features
- Built with **Tkinter** for the GUI
- Integrated **yt-dlp** for video downloading
- Used **ffmpeg** for trimming and format conversion
- Error handling for invalid inputs and downloads
- Packaged with **PyInstaller** for easy distribution

## 🛠️ Tech Stack
- Python
- Tkinter
- yt-dlp
- ffmpeg
- PyInstaller

## 📦 Installation
Make sure you have Python 3.x installed. Then install dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:
- `yt-dlp`
- `ffmpeg` (must be installed and added to PATH)
- `tkinter` (usually comes with Python)
- `psutil` (only if your code uses it)

> 🔎 ffmpeg on Windows: download from https://ffmpeg.org/ and add the `bin` folder to your PATH.  
> On macOS (Homebrew): `brew install ffmpeg`.

## ▶️ How to Run
Clone this repo:

```bash
git clone https://github.com/QuinnLyon1/Youtube-Downloader.git
cd Youtube-Downloader
```

Run the app:

```bash
python Downloader.py
```

## 🖥️ Usage
1. Enter a YouTube URL in the input field.  
2. Set custom start/end times (HH:MM:SS format).  
3. Click **Download** to save the trimmed video.
