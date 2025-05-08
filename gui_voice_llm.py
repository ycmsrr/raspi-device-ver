#!/usr/bin/env python3
# gui_voice_llm.py

import os
import sys
import queue
import json
import subprocess
import threading
import sounddevice as sd
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox
from vosk import Model, KaldiRecognizer

# === Configuration (adjust these paths) ===
VOSK_MODEL_PATH = os.path.expanduser("~/gpt4all-cli/vosk-model-small-en-us-0.15>
LLM_CLI_PATH    = os.path.expanduser("~/llama.cpp/build/bin/llama-cli")
LLM_MODEL_PATH  = os.path.expanduser("~/gpt4all-cli/medicine-llm.Q4_K_M.gguf")
GEN_TOKENS      = "64"
# === Verify model and executable exist ===
for path, desc in [
    (VOSK_MODEL_PATH, "Vosk model directory"),
    (LLM_CLI_PATH,    "llama-cli executable"),
    (LLM_MODEL_PATH,  "LLM model file")
]:
    if not os.path.exists(path):
        messagebox.showerror("Configuration Error", f"{desc} not found: {path}")
        sys.exit(1)

# === Initialize Vosk ASR ===
model = Model(VOSK_MODEL_PATH)
recognizer = KaldiRecognizer(model, 16000)

# === Audio callback to queue ===
audio_queue = queue.Queue()
def audio_callback(indata, frames, time_info, status):
    """Queue raw audio data from microphone."""
    if status:
print(f"WARNING: Audio input error: {status}", file=sys.stderr)
    audio_queue.put(bytes(indata))

def record_and_recognize():
    """Record until silence is detected, then return recognized text."""
    recognizer.Reset()
    with sd.RawInputStream(
        samplerate=16000, blocksize=8000,
        dtype='int16', channels=1,
        callback=audio_callback
    ):
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                return result.get("text", "")

def call_llm(prompt_text):
    """Invoke llama-cli non-interactively and filter out log lines."""
proc = subprocess.run(
        [LLM_CLI_PATH, "-m", LLM_MODEL_PATH, "-p", prompt_text, "-n", GEN_TOKEN>
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    if proc.returncode != 0:
        return f"[ERROR] llama-cli exit {proc.returncode}"
    filtered = []
    for line in proc.stdout.splitlines():
        # skip internal logs and performance lines
        if re.match(r'^\s*\w+ seed:', line): continue
        if re.match(r'^\s*sampler params:', line): continue
        if re.match(r'^\s*sampler chain:', line): continue
        if re.match(r'^\s*llama_perf_', line): continue
        if re.match(r'^\s*\w+\s*=', line): continue
        if re.match(r'^\s*\w+:', line): continue
        if not line.strip(): continue
        if re.match(r'^[^\w]+$', line): continue
        filtered.append(line)
    return " ".join(filtered).strip()
def speak_text(text):
    """Use espeak to speak the text."""
    subprocess.run(["espeak", "-s", "140", text])

class VoiceLLMApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voice Assistant")
        # set window to a fixed smaller size
        self.geometry("480x320")
        self.configure(bg="black")

        # Buttons frame at bottom
        btn_frame = tk.Frame(self, bg="black")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        self.record_btn = tk.Button(
            btn_frame, text=" ^=^n  Record", font=("Helvetica", 14),
            command=self.on_record, bg="green", fg="white",
 padx=10, pady=5
        )
        self.record_btn.pack(side=tk.LEFT, padx=5)

        self.quit_btn = tk.Button(
            btn_frame, text=" ^|^v Exit", font=("Helvetica", 14),
            command=self.on_quit, bg="red", fg="white",
            padx=10, pady=5
        )
        self.quit_btn.pack(side=tk.RIGHT, padx=5)

        # Text area fills remaining space
        self.text_area = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, font=("Helvetica", 12),
            bg="black", fg="white"
        )
        self.text_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pad>
        self.text_area.insert(tk.END, "Tap [ ^=^n  Record] to start...\n\n")
        self.text_area.config(state=tk.DISABLED)

    def append_text(self, msg):
        """Append a message to the text area."""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, msg + "\n\n")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def on_record(self):
        """Disable button and start voice processing in a new thread."""
        self.record_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.process_voice).start()

    def process_voice(self):
        """Full pipeline: ASR  ^f^r LLM  ^f^r display & TTS."""
        self.append_text(" ^=^n  Listening...")
        text = record_and_recognize()
        if not text:
            self.append_text("[Warning] No speech recognized.")
            self.record_btn.config(state=tk.NORMAL)
            return
        self.append_text(f"You: {text}")

        self.append_text(" ^= ^v Thinking...")
        response = call_llm(text)
        self.append_text(f"Assistant: {response}")

        speak_text(response)
        self.record_btn.config(state=tk.NORMAL)

    def on_quit(self):
        """Exit the application."""
        self.destroy()

if __name__ == "__main__":
    app = VoiceLLMApp()
    app.mainloop()
