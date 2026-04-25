import json
import os
import threading

DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.join(os.path.dirname(__file__), "data"),
)
COUNTER_FILE = os.path.join(DATA_DIR, "counter.json")
_lock = threading.Lock()


def _read() -> dict:
    if not os.path.exists(COUNTER_FILE):
        return {}
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = COUNTER_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, COUNTER_FILE)


def next_index(key: str, modulo: int) -> int:
    """Atomically return the next round-robin index for ``key``.

    The returned value is in [0, modulo). The internal counter is also
    persisted so that restarts continue the rotation.
    """
    with _lock:
        data = _read()
        current = int(data.get(key, 0))
        index = current % modulo
        data[key] = current + 1
        _write(data)
        return index
