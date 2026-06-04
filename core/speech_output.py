import re
import subprocess
import threading


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


def stop_speaking() -> None:
    """Kill any in-progress `say` process immediately (called before recording starts)."""
    global _proc
    with _proc_lock:
        if _proc and _proc.poll() is None:
            _proc.kill()
            _proc.wait()
        _proc = None


def speak(text: str) -> None:
    global _proc
    clean = _strip_emojis(text)
    if not clean:
        return
    # Start the new process, killing any currently-running one first.
    with _proc_lock:
        if _proc and _proc.poll() is None:
            _proc.kill()
            _proc.wait()
        _proc = subprocess.Popen(["say", "-r", "150", clean])
    # Wait outside the lock so stop_speaking() can interrupt at any time.
    _proc.wait()
