import time
import numpy as np
import sounddevice as sd
import whisper

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def record_audio(duration: int = 5, sample_rate: int = 16000) -> np.ndarray:
    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", callback=callback):
        time.sleep(duration)

    if not frames:
        return np.zeros(int(sample_rate * duration), dtype="float32")
    return np.concatenate(frames).flatten()


def transcribe(audio: np.ndarray) -> str:
    model = _get_model()
    result = model.transcribe(audio, language="en", fp16=False)
    return result["text"].strip()
