import numpy as np
import sounddevice as sd
import whisper

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def _find_input_device() -> int | None:
    """Return the best available input device index.

    Preference order:
      1. System default input (if it has input channels)
      2. First device whose name contains 'MacBook Pro Microphone' or 'Built-in'
      3. First device with at least one input channel
    Returns None only when no input device is found at all.
    """
    devices = sd.query_devices()

    # Try the system default first
    try:
        default_idx = sd.default.device[0]
        if default_idx >= 0 and devices[default_idx]['max_input_channels'] > 0:
            return default_idx
    except Exception:
        pass

    # Preferred fallback: built-in mic (reliable, always present on Mac)
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and (
            'MacBook Pro Microphone' in dev['name'] or
            'Built-in' in dev['name']
        ):
            return i

    # Last resort: first device with any input channels
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            return i

    return None


def record_audio(duration: int = 5, sample_rate: int = 16000) -> np.ndarray:
    """Record until silence-after-speech or max duration, whichever comes first.

    Strategy:
      - Record in 100 ms chunks
      - Track RMS energy to detect speech vs silence
      - Once speech starts, stop after 1.5 s of consecutive silence
      - Hard-stop at `duration` seconds regardless
    If the preferred device fails (e.g. Bluetooth headset dropped), falls back
    to the built-in MacBook microphone automatically.
    """
    chunk_secs   = 0.1
    chunk_size   = int(sample_rate * chunk_secs)
    silence_secs = 1.5
    speech_thresh = 0.01
    silence_chunks_needed = int(silence_secs / chunk_secs)
    max_chunks = int(duration / chunk_secs)

    def _record_on_device(device):
        frames: list[np.ndarray] = []
        speech_started = False
        silence_count  = 0
        with sd.InputStream(samplerate=sample_rate, channels=1,
                            dtype="float32", device=device) as stream:
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
                        break
        return np.concatenate(frames).flatten() if frames else np.zeros(
            int(sample_rate * duration), dtype="float32")

    primary = _find_input_device()
    try:
        return _record_on_device(primary)
    except sd.PortAudioError:
        # Primary device failed (e.g. Bluetooth dropped) — try built-in mic
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if i != primary and dev['max_input_channels'] > 0 and (
                'MacBook Pro Microphone' in dev['name'] or 'Built-in' in dev['name']
            ):
                return _record_on_device(i)
        raise  # no fallback found — propagate original error


def transcribe(audio: np.ndarray) -> str:
    model = _get_model()
    result = model.transcribe(audio, language="en", fp16=False)
    return result["text"].strip()
