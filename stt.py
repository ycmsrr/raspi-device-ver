from vosk import Model, KaldiRecognizer
import sounddevice as sd
import queue
import sys
import json
import time

# Load model
model = Model("vosk-model-small-en-us-0.15")
recognizer = KaldiRecognizer(model, 16000)

# Recording parameters
samplerate = 16000
device = None  # Default device
q = queue.Queue()

# Silence detection parameters
startup_timeout = 3.0  # 允许开头最多3秒沉默
silence_timeout = 1.0  # 正常说话时，超过1秒静音退出
start_time = time.time()
last_voice_time = None  # 用来记录上一次有讲话的时间

# Audio callback: puts audio data into queue
def callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=device, dtype='int16',
                       channels=1, callback=callback):
    print("Listening... Start speaking within 3 seconds. (Will auto-stop after 1 second of silence)")

    try:
        while True:
            try:
                data = q.get(timeout=0.1)
            except queue.Empty:
                now = time.time()

                if last_voice_time is None:
                    # 一直没说话，检查是不是超过startup_timeout
                    if now - start_time > startup_timeout:
                        print("\nNo speech detected within 3 seconds. Stopping...")
                        break
                else:
                    # 说过话了，检查是不是超过silence_timeout
                    if now - last_voice_time > silence_timeout:
                        print("\nDetected silence after speech. Stopping...")
                        break
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result['text']
                if text.strip() != "":
                    print("You said:", text)
                    last_voice_time = time.time()
            else:
                partial = json.loads(recognizer.PartialResult())
                if partial['partial'].strip() != "":
                    last_voice_time = time.time()

    except KeyboardInterrupt:
        print("\nStopped manually.")
