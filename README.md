# Sania AI Assistant 🎙️🤖

A local, privacy-focused Windows transcription assistant powered by *Faster-Whisper*. 

## ✨ Features
- *Global Hotkey:* Hold Alt + Space to record and transcribe instantly.
- *Auto-Typing:* Automatically types transcribed text into any active window (Word, Notepad, Browser).
- *Privacy First:* Runs entirely on your CPU; no data ever leaves your computer.

## 🚀 Installation

1. *Clone the repository:*
   ```bash
   git clone [https://github.com/YourUsername/Sania_AI_Assistant.git](https://github.com/YourUsername/Sania_AI_Assistant.git)
   cd Sania_AI_Assistant
2.  Set up a Virtual Environment:
   python -m venv venv
   .\venv\Scripts\activate
3.  Install Dependencies:
    pip install -r requirements.txt

## 🛠️ Usage
​Run the assistant: python main.py
​Hold Alt + Space to speak.
​Release the keys to see the AI type your words into your active document!
​
## 📦 Tech Stack
​Python 3.10+
​Faster-Whisper (CTranslate2)
​PyStray (System Tray integration)
​Keyboard & Pyperclip (System interaction)