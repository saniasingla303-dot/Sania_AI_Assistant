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

# 1. SETUP ENGINE
# Using 'base' for high accuracy; 'int8' makes it run fast on your CPU
print("Loading Local AI Engine... (First time will download model files)")
model = WhisperModel("base", device="cpu", compute_type="int8")

recording = False
audio_buffer = []

def callback(indata, frames, time, status):
    if recording:
        audio_buffer.append(indata.copy())

# 2. RECORDING LOGIC
def start_recording():
    global recording, audio_buffer
    if not recording:
        recording = True
        audio_buffer = []
        print("\n[REC] Listening... Release Alt+Space to finish.")
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
        segments, _ = model.transcribe(audio, beam_size=5)
        text = " ".join([s.text for s in segments]).strip()
        
        if text:
            pyperclip.copy(text) # Copies to clipboard
            #keyboard.write(text)  # Types it into your active window
            time.sleep(0.8)  # Wait 0.5 seconds for keys to release
            keyboard.write(text, delay=0.01) # Type slightly slower
            print(f"[SUCCESS] Typed: {text}")

# 3. UI & HOTKEYS
def create_icon():
    image = Image.new('RGB', (64, 64), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.ellipse((10, 10, 50, 50), fill=(0, 120, 215)) # Blue icon
    return image

def run_hotkeys():
    # Detect Alt+Space hold
    keyboard.add_hotkey('alt+space', start_recording, trigger_on_release=False)
    while True:
        if recording and not keyboard.is_pressed('space'):
            stop_and_transcribe()
        sd.sleep(50)

if __name__ == "__main__":
    print("Assistant Active! Hold 'Alt + Space' to transcribe.")
    threading.Thread(target=run_hotkeys, daemon=True).start()
    
    icon = pystray.Icon("WhisperApp", create_icon(), menu=pystray.Menu(
        pystray.MenuItem("Exit", lambda i: os._exit(0))
    ))
    icon.run()