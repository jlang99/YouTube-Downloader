import threading
from pytubefix import YouTube
from tkinter import *
from tkinter import scrolledtext, messagebox
import sys
import ctypes
import requests
import json
import os
import atexit
import time
from io import BytesIO
from PIL import Image, ImageTk

def download():
    submit.config(state=DISABLED)
    output_box.config(state=NORMAL)
    output_box.delete('1.0', END)
    
    try:
        link = link_var.get()
        
        def on_progress_gui(stream, chunk, bytes_remaining):
            total_size = stream.filesize
            bytes_downloaded = total_size - bytes_remaining
            percentage = (bytes_downloaded / total_size) * 100
            
            # Use root.after() to safely update the GUI from a different thread
            # This schedules the update to happen in the main thread
            root.after(0, update_progress, percentage)

        yt = YouTube(link, on_progress_callback=on_progress_gui)
        
        # Display thumbnail
        try:
            thumbnail_url = yt.thumbnail_url
            response = requests.get(thumbnail_url)
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            base_width = 160
            w_percent = (base_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            root.after(0, display_thumbnail, photo) # Safely update thumbnail
            
        except Exception as e:
            root.after(0, lambda: output_box.insert(END, f"Could not load thumbnail: {e}\n"))
        
        root.after(0, lambda: output_box.insert(END, f"Title: {yt.title}\n"))

        if audio.get():
            root.after(0, lambda: output_box.insert(END, "Downloading audio only...\n"))
            yd = yt.streams.filter(only_audio=True).first()
            direct = audio_path_var.get()
        else:
            root.after(0, lambda: output_box.insert(END, "Downloading highest resolution video...\n"))
            yd = yt.streams.get_highest_resolution()
            direct = video_path_var.get()

        root.after(0, lambda: output_box.insert(END, "\n", "progress"))
        
        start_time = time.perf_counter()
        yd.download(direct)
        end_time = time.perf_counter()
        duration = end_time - start_time

        root.after(0, on_download_complete, duration, direct)
    except Exception as e:
        root.after(0, lambda: output_box.insert(END, f"\nAn error occurred: {e}\n"))
    finally:
        root.after(0, reset_gui)
        
def start_download_thread():
    # Create and start a new thread for the download function
    download_thread = threading.Thread(target=download, daemon=True)
    download_thread.start()
    
def update_progress(percentage):
    """Safely updates the progress bar in the main thread."""
    output_box.delete("progress.first", "progress.last")
    bar_length = 40
    filled_len = int(round(bar_length * percentage / 100))
    bar = '█' * filled_len + ' ' * (bar_length - filled_len)
    output_box.insert(END, f'|{bar}| {percentage:.1f}%\n', "progress")
    output_box.see(END)

def display_thumbnail(photo):
    """Safely displays the thumbnail in the main thread."""
    output_box.image = photo
    output_box.image_create(END, image=photo)
    output_box.insert(END, '\n\n')

def on_download_complete(duration, direct):
    """Safely handles post-download tasks in the main thread."""
    output_box.delete("progress.first", "progress.last")
    completion_msg = f"Download complete in {duration:.2f} seconds!\nSaved to: {direct}"
    output_box.insert(END, f"\n{completion_msg}\n")

def reset_gui():
    """Safely resets the GUI elements in the main thread."""
    submit.config(state=NORMAL)
    link_var.set("")
    output_box.config(state=DISABLED)
    output_box.see(END)

    
#Sets the Image to the Taskbar
myappid = 'YT.DL.APP'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# --- Settings Management ---
def get_application_path():
    """Returns the base path for the application, whether running from source or frozen."""
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the path is the directory of the executable
        return os.path.dirname(sys.executable)
    else:
        # If run from a .py file, the path is its directory
        return os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(get_application_path(), 'Youtube Downloader Settings.json')

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return create_default_settings()
    else:
        return create_default_settings()

def create_default_settings():
    user_home = os.path.expanduser('~')
    icon_path = os.path.join(get_application_path(), 'YouTube.ico')
    default_settings = {
        "video_path": os.path.join(user_home, 'Videos'),
        "audio_path": os.path.join(user_home, 'Music'),
        "icon_path": icon_path
    }
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(default_settings, f, indent=4)
    return default_settings

def save_settings():
    settings_to_save = {
        "video_path": video_path_var.get(),
        "audio_path": audio_path_var.get(),
        "icon_path": settings.get('icon_path') #Keeps the original icon path
    }
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings_to_save, f, indent=4)

atexit.register(save_settings)
# --- End Settings Management ---

settings = load_settings()

# Standard Tkinter type GUI Build
root = Tk()
link_var=StringVar()
video_path_var = StringVar(value=settings.get("video_path"))
audio_path_var = StringVar(value=settings.get("audio_path"))

root.title("YouTube Downloader")
root.geometry("600x450")
try:
    root.iconbitmap(settings.get('icon_path'))
except Exception as e:
    print(f"Error loading icon: {e}")

top_frame = Frame(root)
top_frame.pack(pady=5, padx=10, fill=X)

lbl = Label(root, text= "Input YouTube Link to Download", font= ("Calibiri", 14, 'bold'))
lbl.pack(in_=top_frame)

linkstr = Entry(root, textvariable= link_var, justify=LEFT, width= 100)
linkstr.pack(in_=top_frame, fill=X, pady=(0, 10))
linkstr.bind('<Return>', lambda event: start_download_thread()) # Changed this line

video_path_label = Label(root, text="Video Save Path:")
video_path_label.pack(in_=top_frame, anchor=W)
video_path_entry = Entry(root, textvariable=video_path_var)
video_path_entry.pack(in_=top_frame, fill=X)

audio_path_label = Label(root, text="Audio Save Path:")
audio_path_label.pack(in_=top_frame, anchor=W, pady=(5, 0))
audio_path_entry = Entry(root, textvariable=audio_path_var)
audio_path_entry.pack(in_=top_frame, fill=X)

audio = BooleanVar()
audioToggle = Checkbutton(root, text="Audio Only", variable=audio)
audioToggle.pack(in_=top_frame, pady=5)

activity_log_label = Label(root, text="Activity Log:")
activity_log_label.pack(padx=10, pady=(10, 0), anchor=W)

output_box = scrolledtext.ScrolledText(root, wrap=WORD, height=10, state=DISABLED)
output_box.pack(pady=(2, 10), padx=10, fill=BOTH, expand=True)

submit = Button(root, command=start_download_thread, text="Submit", bg='#FF9999', font=('Calibiri', 14, 'bold')) # Changed this line
submit.pack(fill='x', expand=True, padx=10, pady=(0, 10))

# Tkinter Start
root.mainloop()