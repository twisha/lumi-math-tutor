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


def _clean_for_speech(text: str) -> str:
    """Strip markdown and visual content that should never be read aloud."""
    # Remove fenced code blocks entirely
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Strip markdown bold/italic/inline-code so say() doesn't read "asterisk asterisk"
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)   # **bold** → bold
    text = re.sub(r'\*(.+?)\*',     r'\1', text)   # *italic* → italic
    text = re.sub(r'`([^`]+)`',     r'\1', text)   # `code` → code
    # Remove lines that look like visual helper content
    _SKIP = ('visual helper', 'number line', '•', '* ', '- ')
    lines = [
        ln for ln in text.splitlines()
        if not any(ln.strip().lower().startswith(p) for p in _SKIP)
    ]
    text = ' '.join(ln.strip() for ln in lines if ln.strip())
    # Remove inline number sequences like "9, 10, 11, 12" (3+ consecutive numbers)
    text = re.sub(r'(\b\d+\b,\s*){2,}\b\d+\b', '', text)
    # Replace standalone ? placeholder (e.g. "the ? circle") — space on both sides only
    text = re.sub(r'(?<=\s)\?(?=\s)', 'question mark', text)
    # Collapse excess whitespace
    return re.sub(r'\s{2,}', ' ', text).strip()


def _normalize(text: str) -> str:
    """Normalize Unicode punctuation that confuses the say command."""
    return (
        text
        .replace('—', ', ')   # em dash  —  → comma pause
        .replace('–', ', ')   # en dash  –  → comma pause
        .replace('’', "'")    # right single quote '
        .replace('‘', "'")    # left single quote  '
        .replace('“', '"')    # left double quote  "
        .replace('”', '"')    # right double quote "
        .replace('…', '...')  # ellipsis …
    )


def speak(text: str) -> None:
    global _proc
    clean = _normalize(_strip_emojis(_clean_for_speech(text)))
    if not clean:
        return
    with _proc_lock:
        if _proc and _proc.poll() is None:
            _proc.kill()
            _proc.wait()
        # Feed text via stdin so no CLI arg escaping issues
        _proc = subprocess.Popen(
            ["say", "-r", "150", "-f", "-"],
            stdin=subprocess.PIPE
        )
        # [[slnc 500]] keeps the process alive 500 ms after the last word
        # so the audio buffer fully flushes before say exits.
        _proc.stdin.write((clean + " [[slnc 500]]").encode("utf-8"))
        _proc.stdin.close()
    _proc.wait()
