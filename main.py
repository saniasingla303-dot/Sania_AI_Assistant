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
model = None
recording = False
audio_buffer = []
is_loading_model = False # Safety lock

def load_model(model_size, icon=None):
    global model, current_model_name, is_loading_model
    
    is_loading_model = True
    print(f"\n[SYSTEM] Preparing to load '{model_size}' model...")
    
    if icon:
        # Triggers a native Windows popup notification!
        icon.notify(f"Downloading/Loading '{model_size}' model.\nThis may take a minute...", "AI Model Switching")

    try:
        # INDUSTRY STANDARD: Clear the old model from RAM before loading a new one
        if model is not None:
            del model
            gc.collect() 

        # --- DYNAMIC HARDWARE DETECTION ---
        try:
            # First, attempt to load the model on a dedicated NVIDIA GPU
            model = WhisperModel(model_size, device="cuda", compute_type="float16")
            print(f"[SYSTEM] Hardware Check: NVIDIA GPU detected! Running on GPU 🚀")
        except Exception:
            # If no CUDA GPU is found (like on standard laptops), fallback to CPU
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            print(f"[SYSTEM] Hardware Check: No GPU detected. Safely falling back to CPU 🐢")
        # ----------------------------------
        
        current_model_name = model_size
        print(f"[SYSTEM] Successfully loaded the {current_model_name} model!")
        
        if icon:
            icon.notify(f"Successfully switched to '{model_size}' model!", "AI Ready")

    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        if icon:
            icon.notify(f"Error loading model. Check terminal.", "System Error")
    
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
    # 1. Load the initial base model on startup
    print("Booting up Sania AI Assistant...")
    load_model("base")
    
    # 2. Start the hotkey listener in the background
    threading.Thread(target=run_hotkeys, daemon=True).start()
    
    # 3. Build the dynamic System Tray menu
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

    print("Assistant Active! Check your system tray (bottom right) for the menu.")
    icon = pystray.Icon("WhisperApp", create_icon(), menu=menu)
    icon.run()