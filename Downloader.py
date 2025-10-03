"""
YouTube Clip Downloader

Requirements:
- Python 3.x
- yt-dlp (pip install yt-dlp)
- ffmpeg (must be installed and in PATH)

How to run:
    python Downloader

How to convert to EXE (optional):
    pip install pyinstaller
    pyinstaller --onefile Downloader
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import tkinter.font as tkFont
import subprocess
import re
import os
import threading
import webbrowser
from datetime import datetime
import signal
import psutil
from pathlib import Path

# --- Helper Functions ---
def is_valid_url(url):
    # Simple YouTube URL check
    return re.match(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$", url)

def is_valid_time(h, m, s):
    # Check HH:MM:SS format
    try:
        hours = int(h) if h else 0
        minutes = int(m) if m else 0
        seconds = int(s) if s else 0
        return 0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59
    except ValueError:
        return False

def format_time(h, m, s):
    """Convert separate H,M,S to HH:MM:SS format"""
    hours = int(h) if h else 0
    minutes = int(m) if m else 0
    seconds = int(s) if s else 0
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def format_time_for_filename(time_str):
    """Convert HH:MM:SS format to HH-MM-SS for safe filename"""
    return time_str.replace(':', '-')

def sanitize_filename(title):
    """Sanitize video title to create a safe filename"""
    import string
    # Remove or replace illegal filename characters
    illegal_chars = '<>:"/\\|?*'
    safe_chars = string.ascii_letters + string.digits + ' -_'
    
    # Replace illegal characters with underscores
    for char in illegal_chars:
        title = title.replace(char, '_')
    
    # Remove any other non-safe characters
    safe_title = ''.join(c for c in title if c in safe_chars)
    
    # Remove leading/trailing spaces and underscores
    safe_title = safe_title.strip(' _')
    
    # Limit length to avoid filesystem issues
    if len(safe_title) > 100:
        safe_title = safe_title[:100]
    
    # Ensure we have a valid filename
    if not safe_title:
        safe_title = "youtube_video"
    
    return safe_title

def get_video_title(url):
    """Get video title using yt-dlp --get-title"""
    try:
        cmd = f'yt-dlp --get-title "{url}"'
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if result.returncode == 0:
            title = result.stdout.strip()
            return sanitize_filename(title)
        else:
            return None
    except Exception as e:
        print(f"Error getting video title: {e}")
        return None

def run_command(cmd, process_callback=None):
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if process_callback:
            process_callback(process)
        result = process.communicate()
        return process.returncode, result[0] + result[1]
    except Exception as e:
        return 1, str(e)

def download_and_clip(url, start, end, status_callback, cancel_callback):
    status_callback("Starting download...")
    
    # Create downloads directory at specified location
    download_dir = Path.home() / "Downloads" / "YouTubeClips"
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Get video title and create safe filename
    video_title = get_video_title(url)
    if not video_title:
        video_title = f"yt_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Format times for filename (replace colons with dashes)
    start_time_filename = format_time_for_filename(start)
    end_time_filename = format_time_for_filename(end)
    
    # Generate filenames using video title
    full_output = str((download_dir / f"{video_title}_full.mp4").resolve())
    clipped_output = str((download_dir / f"{video_title}_clip_{start_time_filename}_to_{end_time_filename}.mp4").resolve())
    
    # Always download full video with specific format selection
    status_callback(f"Downloading: {video_title}")
    
    # Check if cookies.txt exists in the script directory
    script_dir = Path(__file__).parent
    cookies_path = script_dir / "cookies.txt"
    cookies_arg = f'--cookies "{cookies_path}"' if cookies_path.exists() else ""
    
    # Define player clients to try in order of preference
    player_clients = [
        ("android", "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36", "https://m.youtube.com/"),
        ("web", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "https://www.youtube.com/"),
        ("ios", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1", "https://m.youtube.com/")
    ]
    
    # Fallback loop to try different player clients
    download_success = False
    for client_name, user_agent, referer in player_clients:
        if cancel_callback():
            status_callback("Download cancelled.")
            return
        
        status_callback(f"Trying {client_name} player client...")
        
        # Build yt-dlp command for current client
        ytdlp_cmd = (
            f'yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]" '
            f'--merge-output-format mp4 '
            f'--extractor-args "youtube:player_client={client_name}" '
            f'--retries 10 '
            f'--fragment-retries 10 '
            f'--concurrent-fragments 5 '
            f'--user-agent "{user_agent}" '
            f'--referer "{referer}" '
            f'--add-header "Accept-Language: en-US,en;q=0.9" '
            f'--add-header "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" '
            f'--add-header "Accept-Encoding: gzip, deflate, br" '
            f'--add-header "DNT: 1" '
            f'--add-header "Connection: keep-alive" '
            f'--add-header "Upgrade-Insecure-Requests: 1" '
            f'--add-header "Sec-Fetch-Dest: document" '
            f'--add-header "Sec-Fetch-Mode: navigate" '
            f'--add-header "Sec-Fetch-Site: none" '
            f'--no-check-certificates '
            f'--prefer-insecure '
            f'--no-warnings '
            f'--no-playlist '
            f'{cookies_arg} '
            f'-o "{full_output}" '
            f'"{url}"'
        )
        
        process = None
        def set_process(p):
            nonlocal process
            process = p
        
        code, output = run_command(ytdlp_cmd, set_process)
        
        # Check for cancellation
        if cancel_callback():
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
            status_callback("Download cancelled.")
            return
        
        # Check if download was successful
        if code == 0 and Path(full_output).exists():
            status_callback(f"✅ Download successful using {client_name} player client!")
            download_success = True
            break
        else:
            status_callback(f"❌ {client_name} client failed: {output}")
            # Clean up any partial download
            if Path(full_output).exists():
                try:
                    Path(full_output).unlink()
                except:
                    pass
    
    # If all clients failed, try generic extractor as a last resort
    if not download_success:
        status_callback("All player clients failed. Trying generic extractor as fallback...")
        ytdlp_cmd = (
            f'yt-dlp --force-generic-extractor '
            f'-f "bestvideo[ext=mp4]+bestaudio[ext=m4a]" '
            f'--merge-output-format mp4 '
            f'--retries 10 '
            f'--fragment-retries 10 '
            f'--concurrent-fragments 5 '
            f'--no-check-certificates '
            f'--prefer-insecure '
            f'--no-warnings '
            f'--no-playlist '
            f'{cookies_arg} '
            f'-o "{full_output}" '
            f'"{url}"'
        )
        process = None
        def set_process(p):
            nonlocal process
            process = p
        code, output = run_command(ytdlp_cmd, set_process)
        if cancel_callback():
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
            status_callback("Download cancelled.")
            return
        if code == 0 and Path(full_output).exists():
            status_callback("✅ Download successful using generic extractor!")
            download_success = True
        else:
            status_callback(f"❌ Generic extractor failed: {output}")
            if Path(full_output).exists():
                try:
                    Path(full_output).unlink()
                except:
                    pass
            status_callback("❌ All extraction methods failed. Download cannot proceed.")
            return
    
    # Trim with ffmpeg using best practices
    status_callback("Trimming video with ffmpeg...")
    ffmpeg_cmd = (
        f'ffmpeg -y -i "{full_output}" -ss {start} -to {end} '
        f'-map 0:v:0 -map 0:a:0? '
        f'-c:v libx264 -preset veryslow -crf 18 '
        f'-c:a aac -b:a 256k '
        f'-vsync 2 -copyts -avoid_negative_ts make_zero -reset_timestamps 1 '
        f'-movflags +faststart '
        f'-shortest "{clipped_output}"'
    )
    
    code, output = run_command(ffmpeg_cmd, set_process)
    
    # Check for cancellation
    if cancel_callback():
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        status_callback("Trimming cancelled.")
        if Path(full_output).exists():
            Path(full_output).unlink()
        return
    
    if code == 0 and Path(clipped_output).exists():
        status_callback(f"Clip saved as {clipped_output}!")
        # Clean up the full download after trimming
        Path(full_output).unlink()
    else:
        status_callback(f"ffmpeg failed: {output}")
        if Path(full_output).exists():
            Path(full_output).unlink()

# --- GUI ---
class YTClipperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Clip Downloader")
        self.root.geometry("650x750")
        self.root.configure(bg='#f9f9f9')
        
        # Variables
        self.url = ""
        self.cancel_flag = False
        self.download_thread = None
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create main container
        self.main_frame = tk.Frame(root, bg='#f9f9f9')
        self.main_frame.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Create the single screen layout
        self.create_single_screen()
    
    def create_single_screen(self):
        """Create the single screen layout with all elements"""
        
        # Title
        title_label = tk.Label(self.main_frame, text="YouTube Clip Downloader", 
                              font=('Arial', 28, 'bold'), bg='#f9f9f9', fg='#FF0000')
        title_label.pack(pady=(0, 40))
        
        # URL Input Section
        url_frame = tk.Frame(self.main_frame, bg='#f9f9f9')
        url_frame.pack(fill='x', pady=10)
        
        url_label = tk.Label(url_frame, text="YouTube URL:", 
                            font=('Arial', 14, 'bold'), bg='#f9f9f9', fg='#212121')
        url_label.pack(anchor='w', pady=(0, 8))
        
        self.url_entry = tk.Entry(url_frame, font=('Arial', 12), 
                                 relief='flat', bd=2, bg='white', fg='#212121',
                                 highlightthickness=1, highlightcolor='#0066cc')
        self.url_entry.pack(fill='x', pady=(0, 10))
        self.url_entry.bind('<KeyRelease>', self.validate_url)
        
        # Clickable URL link (optional)
        underline_font = tkFont.Font(family="Arial", size=10, underline=True)
        self.url_link = tk.Label(
            url_frame,
            text="",
            font=underline_font,
            bg="#f9f9f9",
            fg="#0066cc",
            cursor="hand2",
            wraplength=500
        )
        self.url_link.pack(anchor='w', pady=(0, 25))
        self.url_link.bind('<Button-1>', self.open_url)
        
        # Time Input Section
        time_frame = tk.Frame(self.main_frame, bg='#f9f9f9')
        time_frame.pack(fill='x', pady=25)
        
        time_label = tk.Label(time_frame, text="Trim Settings", 
                             font=('Arial', 18, 'bold'), bg='#f9f9f9', fg='#212121')
        time_label.pack(anchor='w', pady=(0, 25))
        
        # Start Time Section
        start_section = tk.Frame(time_frame, bg='#f9f9f9')
        start_section.pack(fill='x', pady=(0, 20))
        
        # Start time header with icon
        start_header = tk.Frame(start_section, bg='#f9f9f9')
        start_header.pack(anchor='w', pady=(0, 12))
        
        # Clock icon (using text symbol)
        clock_icon = tk.Label(start_header, text="🕐", font=('Arial', 16), 
                             bg='#f9f9f9', fg='#FF0000')
        clock_icon.pack(side='left', padx=(0, 8))
        
        start_label = tk.Label(start_header, text="Start Time:", 
                              font=('Arial', 14, 'bold'), bg='#f9f9f9', fg='#212121')
        start_label.pack(side='left')
        
        # Start time inputs with labels
        start_inputs_frame = tk.Frame(start_section, bg='#f9f9f9')
        start_inputs_frame.pack(anchor='w')
        
        # Hours
        hours_frame = tk.Frame(start_inputs_frame, bg='#f9f9f9')
        hours_frame.pack(side='left', padx=(0, 15))
        
        hours_label = tk.Label(hours_frame, text="Hours", 
                              font=('Arial', 10), bg='#f9f9f9', fg='#666666')
        hours_label.pack(pady=(0, 4))
        
        self.start_h = tk.Entry(hours_frame, width=4, font=('Arial', 12), 
                               relief='flat', bd=1, bg='white', fg='#212121',
                               highlightthickness=1, highlightcolor='#FF0000',
                               highlightbackground='#e0e0e0')
        self.start_h.pack()
        
        # Minutes
        minutes_frame = tk.Frame(start_inputs_frame, bg='#f9f9f9')
        minutes_frame.pack(side='left', padx=(0, 15))
        
        minutes_label = tk.Label(minutes_frame, text="Minutes", 
                                font=('Arial', 10), bg='#f9f9f9', fg='#666666')
        minutes_label.pack(pady=(0, 4))
        
        self.start_m = tk.Entry(minutes_frame, width=4, font=('Arial', 12), 
                               relief='flat', bd=1, bg='white', fg='#212121',
                               highlightthickness=1, highlightcolor='#FF0000',
                               highlightbackground='#e0e0e0')
        self.start_m.pack()
        
        # Seconds
        seconds_frame = tk.Frame(start_inputs_frame, bg='#f9f9f9')
        seconds_frame.pack(side='left')
        
        seconds_label = tk.Label(seconds_frame, text="Seconds", 
                                font=('Arial', 10), bg='#f9f9f9', fg='#666666')
        seconds_label.pack(pady=(0, 4))
        
        self.start_s = tk.Entry(seconds_frame, width=4, font=('Arial', 12), 
                               relief='flat', bd=1, bg='white', fg='#212121',
                               highlightthickness=1, highlightcolor='#FF0000',
                               highlightbackground='#e0e0e0')
        self.start_s.pack()
        
        # End Time Section
        end_section = tk.Frame(time_frame, bg='#f9f9f9')
        end_section.pack(fill='x', pady=(0, 20))
        
        # End time header with icon
        end_header = tk.Frame(end_section, bg='#f9f9f9')
        end_header.pack(anchor='w', pady=(0, 12))
        
        # Clock icon (using text symbol)
        end_clock_icon = tk.Label(end_header, text="🕐", font=('Arial', 16), 
                                 bg='#f9f9f9', fg='#FF0000')
        end_clock_icon.pack(side='left', padx=(0, 8))
        
        end_label = tk.Label(end_header, text="End Time:", 
                            font=('Arial', 14, 'bold'), bg='#f9f9f9', fg='#212121')
        end_label.pack(side='left')
        
        # End time inputs with labels
        end_inputs_frame = tk.Frame(end_section, bg='#f9f9f9')
        end_inputs_frame.pack(anchor='w')
        
        # Hours
        end_hours_frame = tk.Frame(end_inputs_frame, bg='#f9f9f9')
        end_hours_frame.pack(side='left', padx=(0, 15))
        
        end_hours_label = tk.Label(end_hours_frame, text="Hours", 
                                  font=('Arial', 10), bg='#f9f9f9', fg='#666666')
        end_hours_label.pack(pady=(0, 4))
        
        self.end_h = tk.Entry(end_hours_frame, width=4, font=('Arial', 12), 
                             relief='flat', bd=1, bg='white', fg='#212121',
                             highlightthickness=1, highlightcolor='#FF0000',
                             highlightbackground='#e0e0e0')
        self.end_h.pack()
        
        # Minutes
        end_minutes_frame = tk.Frame(end_inputs_frame, bg='#f9f9f9')
        end_minutes_frame.pack(side='left', padx=(0, 15))
        
        end_minutes_label = tk.Label(end_minutes_frame, text="Minutes", 
                                    font=('Arial', 10), bg='#f9f9f9', fg='#666666')
        end_minutes_label.pack(pady=(0, 4))
        
        self.end_m = tk.Entry(end_minutes_frame, width=4, font=('Arial', 12), 
                             relief='flat', bd=1, bg='white', fg='#212121',
                             highlightthickness=1, highlightcolor='#FF0000',
                             highlightbackground='#e0e0e0')
        self.end_m.pack()
        
        # Seconds
        end_seconds_frame = tk.Frame(end_inputs_frame, bg='#f9f9f9')
        end_seconds_frame.pack(side='left')
        
        end_seconds_label = tk.Label(end_seconds_frame, text="Seconds", 
                                    font=('Arial', 10), bg='#f9f9f9', fg='#666666')
        end_seconds_label.pack(pady=(0, 4))
        
        self.end_s = tk.Entry(end_seconds_frame, width=4, font=('Arial', 12), 
                             relief='flat', bd=1, bg='white', fg='#212121',
                             highlightthickness=1, highlightcolor='#FF0000',
                             highlightbackground='#e0e0e0')
        self.end_s.pack()
        
        # Set default values
        self.start_h.insert(0, "0")
        self.start_m.insert(0, "0")
        self.start_s.insert(0, "0")
        self.end_h.insert(0, "0")
        self.end_m.insert(0, "1")
        self.end_s.insert(0, "0")
        
        # Action Buttons Section
        button_frame = tk.Frame(self.main_frame, bg='#f9f9f9')
        button_frame.pack(pady=35)
        
        self.trim_btn = tk.Button(button_frame, text="Trim Clip", 
                                 font=('Arial', 14, 'bold'), 
                                 bg='#FF0000', fg='white', 
                                 relief='flat', padx=35, pady=12,
                                 command=self.trim_clip)
        self.trim_btn.pack(side='left', padx=(0, 15))
        
        self.cancel_btn = tk.Button(button_frame, text="Cancel", 
                                   font=('Arial', 14), 
                                   bg='#9E9E9E', fg='white', 
                                   relief='flat', padx=35, pady=12,
                                   command=self.cancel_operation)
        self.cancel_btn.pack(side='left', padx=(0, 15))
        
        # Trim Another Clip button (hidden by default)
        self.trim_another_btn = tk.Button(button_frame, text="Trim Another Clip", 
                                         font=('Arial', 14, 'bold'), 
                                         bg='#4CAF50', fg='white', 
                                         relief='flat', padx=35, pady=12,
                                         command=self.reset_form)
        
        # Status Area
        status_frame = tk.Frame(self.main_frame, bg='#f9f9f9')
        status_frame.pack(fill='x', pady=25)
        
        status_label = tk.Label(status_frame, text="Status:", 
                               font=('Arial', 12, 'bold'), bg='#f9f9f9', fg='#212121')
        status_label.pack(anchor='w')
        
        self.status_area = scrolledtext.ScrolledText(status_frame, height=8, width=60, 
                                                   font=('Arial', 10), state='disabled',
                                                   relief='flat', bd=1, bg='white', fg='#212121')
        self.status_area.pack(fill='x', pady=(8, 0))
    
    def validate_url(self, event=None):
        """Validate URL and update link display"""
        url = self.url_entry.get().strip()
        if is_valid_url(url):
            self.url_link.config(text=url)
        else:
            self.url_link.config(text="")
    
    def open_url(self, event=None):
        """Open the URL in the browser"""
        if self.url and is_valid_url(self.url):
            webbrowser.open(self.url)
    
    def trim_clip(self):
        """Start the download and trim process"""
        # Get and validate URL
        self.url = self.url_entry.get().strip()
        if not is_valid_url(self.url):
            messagebox.showerror("Error", "Please enter a valid YouTube URL.")
            return
        
        # Validate time inputs
        start_h = self.start_h.get().strip()
        start_m = self.start_m.get().strip()
        start_s = self.start_s.get().strip()
        end_h = self.end_h.get().strip()
        end_m = self.end_m.get().strip()
        end_s = self.end_s.get().strip()
        
        if not (is_valid_time(start_h, start_m, start_s) and is_valid_time(end_h, end_m, end_s)):
            messagebox.showerror("Error", "Please enter valid time format (HH:MM:SS).")
            return
        
        start_time = format_time(start_h, start_m, start_s)
        end_time = format_time(end_h, end_m, end_s)
        
        # Clear status area
        self.status_area.config(state='normal')
        self.status_area.delete(1.0, tk.END)
        self.status_area.config(state='disabled')
        
        # Disable buttons during process
        self.trim_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        
        # Reset cancel flag
        self.cancel_flag = False
        
        # Start download in thread
        def download_task():
            try:
                download_and_clip(self.url, start_time, end_time, self.set_status, self.is_cancelled)
                # Check if download was successful (not cancelled)
                if not self.cancel_flag:
                    self.show_trim_another_button()
            finally:
                self.trim_btn.config(state='normal')
                self.cancel_btn.config(state='disabled')
        
        self.download_thread = threading.Thread(target=download_task, daemon=True)
        self.download_thread.start()
    
    def cancel_operation(self):
        """Cancel the current operation"""
        self.cancel_flag = True
        self.set_status("Cancelling...")
    
    def is_cancelled(self):
        """Check if operation should be cancelled"""
        return self.cancel_flag
    
    def show_trim_another_button(self):
        """Show the Trim Another Clip button after successful download"""
        self.trim_another_btn.pack(side='left', padx=(15, 0))
    
    def reset_form(self):
        """Reset the form to initial state"""
        # Clear URL entry
        self.url_entry.delete(0, tk.END)
        self.url_link.config(text="")
        
        # Reset time inputs to defaults
        self.start_h.delete(0, tk.END)
        self.start_h.insert(0, "0")
        self.start_m.delete(0, tk.END)
        self.start_m.insert(0, "0")
        self.start_s.delete(0, tk.END)
        self.start_s.insert(0, "0")
        
        self.end_h.delete(0, tk.END)
        self.end_h.insert(0, "0")
        self.end_m.delete(0, tk.END)
        self.end_m.insert(0, "1")
        self.end_s.delete(0, tk.END)
        self.end_s.insert(0, "0")
        
        # Clear status area
        self.status_area.config(state='normal')
        self.status_area.delete(1.0, tk.END)
        self.status_area.config(state='disabled')
        
        # Hide Trim Another Clip button
        self.trim_another_btn.pack_forget()
        
        # Reset variables
        self.url = ""
        self.cancel_flag = False
        self.download_thread = None
    
    def set_status(self, msg):
        """Update status area with message"""
        self.status_area.config(state='normal')
        self.status_area.insert(tk.END, msg + '\n')
        self.status_area.see(tk.END)
        self.status_area.config(state='disabled')
        self.root.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = YTClipperApp(root)
    root.mainloop()
