#!/usr/bin/env python3
# voice2llm_vosk_filtered.py

import os
import sys
import queue
import json
import subprocess
import sounddevice as sd
import re
from vosk import Model, KaldiRecognizer

# === Configuration (adjust these paths) ===
VOSK_MODEL_PATH = os.path.expanduser("~/gpt4all-cli/vosk-model-small-en-us-0.15")
LLM_CLI_PATH    = os.path.expanduser("~/llama.cpp/build/bin/llama-cli")
LLM_MODEL_PATH  = os.path.expanduser("~/gpt4all-cli/medicine-llm.Q4_K_M.gguf")
GEN_TOKENS      = "64"

# === Verify model files and executable exist ===
for path, desc in [
    (VOSK_MODEL_PATH, "Vosk model directory"),
    (LLM_CLI_PATH,    "llama-cli executable"),
    (LLM_MODEL_PATH,  "LLM model file")
]:
    if not os.path.exists(path):
        sys.exit(f"ERROR: {desc} not found at {path}")

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

# === Record until silence and return recognized text ===
def record_and_recognize():
    print("🎤 Please speak now (recording)...")
    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=audio_callback
    ):
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                return result.get("text", "")

# === Call llama-cli in non-interactive mode and filter logs ===
def call_llm(prompt_text):
    print("🤖 Invoking llama-cli for inference...")
    proc = subprocess.run(
        [
            LLM_CLI_PATH,
            "-m", LLM_MODEL_PATH,
            "-p", prompt_text,
            "-n", GEN_TOKENS
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    if proc.returncode != 0:
        print(f"ERROR: llama-cli exited with code {proc.returncode}")
        print(proc.stdout)
        return None

    filtered_lines = []
    for line in proc.stdout.splitlines():
        # skip collected log prefixes key:value
        if re.match(r'^\s*\w+ seed:', line):      # sampler seed
            continue
        if re.match(r'^\s*sampler params:', line):# sampler params
            continue
        if re.match(r'^\s*sampler chain:', line): # sampler chain
            continue
        if re.match(r'^\s*llama_perf_', line):    # perf logs
            continue
        if re.match(r'^\s*\w+\s*=', line):        # parameter assignments
            continue
        if re.match(r'^\s*\w+:', line):           # other key:value logs
            continue
        if not line.strip():                      # empty line
            continue
        if re.match(r'^[^\w]+$', line):           # punctuation-only
            continue
        filtered_lines.append(line)
    return " ".join(filtered_lines).strip()

# === Text-to-speech via espeak ===
def speak_text(text):
    print("🔊 Speaking response...")
    subprocess.run(["espeak", "-s", "140", text])

# === Main flow ===
def main():
    # 1. ASR
    recognized = record_and_recognize()
    if not recognized:
        print("WARNING: No speech recognized. Please try again.")
        return
    print(f"📝 Recognized: {recognized}")

    # 2. LLM inference
    response = call_llm(recognized)
    if not response:
        print("ERROR: No valid response from model.")
        return
    print(f"🧑‍⚕️ Model response:\n{response}")

    # 3. TTS
    speak_text(response)

if __name__ == "__main__":
    main()
