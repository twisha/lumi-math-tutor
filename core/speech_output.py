import os
import re
import subprocess
import tempfile
import threading

import numpy as np
import scipy.io.wavfile
import sounddevice as sd


def _strip_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text).strip()


_proc: subprocess.Popen | None = None
_proc_lock = threading.Lock()
_sd_playing = False


def list_output_devices() -> list[dict]:
    """Return all available output devices as list of {index, name}."""
    return [
        {"index": i, "name": dev["name"]}
        for i, dev in enumerate(sd.query_devices())
        if dev["max_output_channels"] > 0
    ]


def stop_speaking() -> None:
    """Kill any in-progress speech immediately (called before recording starts)."""
    global _proc, _sd_playing
    with _proc_lock:
        if _proc and _proc.poll() is None:
            _proc.kill()
            _proc.wait()
        _proc = None
    if _sd_playing:
        sd.stop()


def _clean_for_speech(text: str) -> str:
    """Strip markdown and visual content that should never be read aloud."""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'`([^`]+)`',     r'\1', text)
    _SKIP = ('visual helper', 'number line', '•', '* ', '- ')
    lines = [
        ln for ln in text.splitlines()
        if not any(ln.strip().lower().startswith(p) for p in _SKIP)
    ]
    text = ' '.join(ln.strip() for ln in lines if ln.strip())
    text = re.sub(r'(\b\d+\b,\s*){2,}\b\d+\b', '', text)
    text = re.sub(r'(?<=\s)\?(?=\s)', 'question mark', text)
    return re.sub(r'\s{2,}', ' ', text).strip()


def _normalize(text: str) -> str:
    """Normalize Unicode punctuation that confuses the say command."""
    return (
        text
        .replace('—', ', ')
        .replace('–', ', ')
        .replace('‘', "'")
        .replace('’', "'")
        .replace('“', '"')
        .replace('”', '"')
        .replace('…', '...')
    )


def speak(text: str, device: int | None = None) -> None:
    global _proc, _sd_playing
    clean = _normalize(_strip_emojis(_clean_for_speech(text)))
    if not clean:
        return

    if device is None:
        # Default path: stream directly to system default output via say
        with _proc_lock:
            if _proc and _proc.poll() is None:
                _proc.kill()
                _proc.wait()
            _proc = subprocess.Popen(
                ["say", "-r", "150", "-f", "-"],
                stdin=subprocess.PIPE
            )
            _proc.stdin.write((clean + " [[slnc 500]]").encode("utf-8"))
            _proc.stdin.close()
            proc_ref = _proc
        proc_ref.wait()
    else:
        # Device-specific path: generate WAV with say, play via sounddevice
        tmpfile = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmpfile = f.name

            with _proc_lock:
                if _proc and _proc.poll() is None:
                    _proc.kill()
                    _proc.wait()
                _proc = subprocess.Popen(
                    ["say", "-r", "150", "-o", tmpfile,
                     "--data-format=LEI16@22050", "-f", "-"],
                    stdin=subprocess.PIPE
                )
                _proc.stdin.write(clean.encode("utf-8"))
                _proc.stdin.close()
                proc_ref = _proc
            proc_ref.wait()

            if proc_ref.returncode == 0 and os.path.exists(tmpfile):
                rate, data = scipy.io.wavfile.read(tmpfile)
                audio = data.astype(np.float32) / 32768.0
                _sd_playing = True
                try:
                    sd.play(audio, rate, device=device, blocking=True)
                finally:
                    _sd_playing = False
        finally:
            if tmpfile and os.path.exists(tmpfile):
                os.unlink(tmpfile)
