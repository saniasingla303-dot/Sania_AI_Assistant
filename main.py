import tkinter as tk
from tkinter import ttk
from tkinter import messagebox  # <-- NEW: For terminal-style popups
import keyboard
import sounddevice as sd
import numpy as np
import pyperclip
from faster_whisper import WhisperModel
import threading
import pystray
from PIL import Image, ImageDraw
import os
import time
import gc  # Garbage Collection for memory management


# --- 1. GLOBAL STATE & AI SETUP ---
current_model_name = "base"
current_language_mode = "English"
first_boot = True  # <-- NEW: Tracks if the app just started
model = None
recording = False
audio_buffer = []
is_loading_model = False # Safety lock
root = None # Added this here to fix Pylance warning!


# --- VISUAL LOADING UI (PRE-BUILT ARCHITECTURE) ---
def setup_ui():
    global root, loading_window, progress_bar, loading_label
    
    # Initialize the main hidden Tkinter engine
    root = tk.Tk()
    root.withdraw()
    
    # PRE-BUILD the loading window so it's ready instantly
    loading_window = tk.Toplevel(root)
    loading_window.title("Sania AI Assistant")
    # Bulletproof window centering (No 'eval' required!)
    window_width = 350
    window_height = 120
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int((screen_width - window_width) / 2)
    center_y = int((screen_height - window_height) / 2)
    
    loading_window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
    loading_window.attributes('-topmost', True)
    
    # Prevent the user from manually closing the loading box and breaking the app
    loading_window.protocol("WM_DELETE_WINDOW", lambda: None) 
    
    # Create the labels and progress bar once
    loading_label = tk.Label(loading_window, text="Preparing AI Model...", font=("Segoe UI", 11, "bold"))
    loading_label.pack(pady=10)
    
    tk.Label(loading_window, text="Downloading/Loading in progress. Please wait...", font=("Segoe UI", 9)).pack()
    
    progress_bar = ttk.Progressbar(loading_window, mode='indeterminate', length=280)
    progress_bar.pack(pady=10)
    
    # Keep it hidden until we need it!
    loading_window.withdraw()

def show_loading_ui(model_name):
    # Just update the text and make it visible! (Takes 0.001 seconds)
    loading_label.config(text=f"Preparing AI Model: {model_name}")
    progress_bar.start(15)
    loading_window.deiconify() 
    loading_window.update() 

def hide_loading_ui():
    # Stop the animation and hide it again
    progress_bar.stop()
    loading_window.withdraw()


def load_model(model_size, icon=None):
    global model, current_model_name, is_loading_model, first_boot
    
    is_loading_model = True
    
     # 1. Show Native Windows Toast Popup FIRST
    if icon:
        icon.notify("Please wait. This may take a minute depending on your internet speed.", f"Loading Model: {model_size}...")

    # Give the popup 0.5 seconds to start sliding in smoothly
    time.sleep(0.5)

    # 2. Instantly show the pre-built visual progress window
    if root is not None:
        root.after(0, show_loading_ui, model_size)

    # 3. BREATHE: Give Windows time to fully draw the green bar before AI takes the CPU
    time.sleep(1.0)

    try:
        # Clear old memory
        if model is not None:
            del model
            gc.collect() 

        # --- DYNAMIC HARDWARE DETECTION ---
        try:
            model = WhisperModel(model_size, device="cuda", compute_type="float16")
            hw_status = "Hardware Check: NVIDIA GPU detected! Running on GPU 🚀"
        except Exception:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            hw_status = "Hardware Check: No GPU detected. Safely falling back to CPU 🐢"
        # ----------------------------------
        
        current_model_name = model_size
        
        # 4. HIDE the UI window safely BEFORE showing success popups
        if root is not None:
            root.after(0, hide_loading_ui)
        
        # Breathe again to let the window vanish cleanly
        time.sleep(0.5)
        
        # 5. Success Notification (System Tray)
        if icon:
            icon.notify(f"Successfully connected to the {model_size} model. Press Ctrl+Space to talk!", "AI Ready")

        # 6. The "Terminal" Popup for the end user (Only on first boot)
        if first_boot:
            welcome_msg = f"Booting up Sania AI Assistant...\n\n[SYSTEM] Preparing '{model_size}' model...\n[SYSTEM] {hw_status}\n\nAssistant Active! Check your system tray (bottom right) for the menu."
            if root is not None:
                root.after(0, lambda: messagebox.showinfo("System Initialization", welcome_msg))
            first_boot = False

    except Exception as e:
        if root is not None:
            root.after(0, hide_loading_ui)
        if icon:
            icon.notify(f"Failed to load the model. Check your internet connection.", "System Error")
    
    finally:
        is_loading_model = False
        

# --- 2. RECORDING LOGIC ---
def callback(indata, frames, time, status):
    if recording:
        audio_buffer.append(indata.copy())

def start_recording():
    global recording, audio_buffer
    
    # SAFETY LOCK: Prevent recording if the AI is currently swapping models
    if is_loading_model:
        print("[WARNING] Cannot record right now. AI model is currently loading.")
        return

    if not recording:
        recording = True
        audio_buffer = []
        print(f"\n[REC] Listening ({current_model_name} model)... Release Alt+Space to finish.")
        with sd.InputStream(samplerate=16000, channels=1, callback=callback):
            while recording:
                sd.sleep(100)

def stop_and_transcribe():
    global recording
    if recording:
        recording = False
        print("[AI] Transcribing...")
        
        if not audio_buffer: return

        audio = np.concatenate(audio_buffer, axis=0).flatten()
        
        # --- NEW HINGLISH LOGIC ---
        # Determine language rules based on user selection
        if current_language_mode == "Hinglish":
            # The "Super Prompt": Forces the AI to understand WhatsApp slang and English mixing
            prompt = "Haan bhai, main theek hoon. Aap kaise ho? Yeh ek professional document hai. Aap bahut intelligent ho. Theek hai?"
            segments, _ = model.transcribe(audio, beam_size=5, language="en", initial_prompt=prompt)
            
        else:
            # Standard English mode
            prompt = "Hello. This is a professional document, with proper commas, and full stops."
            segments, _ = model.transcribe(audio, beam_size=5, language="en", initial_prompt=prompt)

        text = " ".join([s.text for s in segments]).strip()
        
        if text:
            # The bulletproof Paste & Escape method
            pyperclip.copy(text) 
            time.sleep(0.5) 
            
            keyboard.send('ctrl+v') 
            print(f"[SUCCESS] Typed: {text}")

# --- 3. UI, MENU & HOTKEYS ---
def create_icon():
    image = Image.new('RGB', (64, 64), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.ellipse((10, 10, 50, 50), fill=(0, 120, 215)) 
    return image

def on_menu_click(icon, item):
    target_model = str(item.text)
    
    # Only switch if they clicked a different model, and we aren't already loading one
    if target_model != current_model_name and not is_loading_model:
        # INDUSTRY STANDARD: Run the heavy loading process on a background thread so the UI doesn't freeze
        threading.Thread(target=load_model, args=(target_model, icon), daemon=True).start()

def on_language_click(icon, item):
    global current_language_mode
    current_language_mode = str(item.text)
    print(f"[SYSTEM] Language mode changed to: {current_language_mode}")

def run_hotkeys():
    keyboard.add_hotkey('ctrl+space', start_recording, trigger_on_release=False)
    while True:
        if recording and not keyboard.is_pressed('space'):
            stop_and_transcribe()
        sd.sleep(50)

if __name__ == "__main__":
    print("Booting up Sania AI Assistant...")
    
    # 1. Run the new UI Setup function (Pre-builds the hidden window)
    setup_ui()
    
    # 2. Build the System Tray menu
    menu = pystray.Menu(
        pystray.MenuItem('Select AI Model', pystray.Menu(
            pystray.MenuItem('tiny', on_menu_click, radio=True, checked=lambda item: current_model_name == 'tiny'),
            pystray.MenuItem('base', on_menu_click, radio=True, checked=lambda item: current_model_name == 'base'),
            pystray.MenuItem('small', on_menu_click, radio=True, checked=lambda item: current_model_name == 'small'),
            pystray.MenuItem('medium', on_menu_click, radio=True, checked=lambda item: current_model_name == 'medium'),
            pystray.MenuItem('large', on_menu_click, radio=True, checked=lambda item: current_model_name == 'large')
        )),
        pystray.MenuItem('Select Language', pystray.Menu(
            pystray.MenuItem('English', on_language_click, radio=True, checked=lambda item: current_language_mode == 'English'),
            pystray.MenuItem('Hinglish', on_language_click, radio=True, checked=lambda item: current_language_mode == 'Hinglish')
        )),
        pystray.MenuItem('Exit', lambda i: os._exit(0))
    )

    icon = pystray.Icon("WhisperApp", create_icon(), menu=menu)
    
    # 3. CRITICAL: Run the System Tray in a DETACHED background thread
    icon.run_detached()

    # 4. Start the hotkey listener and initial model load in the background
    threading.Thread(target=run_hotkeys, daemon=True).start()
    threading.Thread(target=load_model, args=("base", icon), daemon=True).start()

    # 5. Run the UI Mainloop (This keeps the app alive and crash-free!)
    root.mainloop()

    