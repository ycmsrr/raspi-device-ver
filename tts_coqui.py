from TTS.api import TTS
import os

# Load a pre-trained TTS model
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)

# Text that needs to be converted to speech
text = "Hello, how can I assist you today?"

# Generate speech and save it to a file
tts.tts_to_file(text=text, file_path="output.wav")

# Play the generated speech
os.system("aplay output.wav")

