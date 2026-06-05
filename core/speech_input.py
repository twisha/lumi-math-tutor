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
    """Record until silence-after-speech or max duration, whichever comes first.

    Strategy:
      - Record in 100 ms chunks
      - Track RMS energy to detect speech vs silence
      - Once speech starts, stop after 1.5 s of consecutive silence
      - Hard-stop at `duration` seconds regardless
    """
    chunk_secs   = 0.1          # chunk size in seconds
    chunk_size   = int(sample_rate * chunk_secs)
    silence_secs = 1.5          # stop this long after speech ends
    speech_thresh = 0.01        # RMS above this = speech detected
    silence_chunks_needed = int(silence_secs / chunk_secs)  # 15 chunks
    max_chunks = int(duration / chunk_secs)

    frames: list[np.ndarray] = []
    speech_started = False
    silence_count  = 0

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            frames.append(chunk.copy())

            rms = float(np.sqrt(np.mean(chunk ** 2)))

            if rms > speech_thresh:
                speech_started = True
                silence_count = 0
            elif speech_started:
                silence_count += 1
                if silence_count >= silence_chunks_needed:
                    break  # child finished speaking — stop early

    if not frames:
        return np.zeros(int(sample_rate * duration), dtype="float32")
    return np.concatenate(frames).flatten()


def transcribe(audio: np.ndarray) -> str:
    model = _get_model()
    result = model.transcribe(audio, language="en", fp16=False)
    return result["text"].strip()
