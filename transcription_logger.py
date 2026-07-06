import os
import csv
import threading
from datetime import datetime
from typing import Optional

LOG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'WhisperDict')
LOG_PATH = os.path.join(LOG_DIR, 'history.csv')
MAX_ENTRIES = 1000


class TranscriptionLogger:
    def __init__(self, enabled: bool = True, max_entries: int = MAX_ENTRIES):
        self.enabled = enabled
        self.max_entries = max_entries
        self._lock = threading.Lock()
        if enabled:
            os.makedirs(LOG_DIR, exist_ok=True)

    def log(self, text: str, duration: Optional[float] = None) -> None:
        if not self.enabled or not text:
            return
        with self._lock:
            try:
                exists = os.path.exists(LOG_PATH)
                with open(LOG_PATH, 'a', newline='', encoding='utf-8') as f:
                    w = csv.writer(f)
                    if not exists:
                        w.writerow(['timestamp', 'text', 'duration_s'])
                    w.writerow([
                        datetime.now().isoformat(),
                        text,
                        f'{duration:.2f}' if duration is not None else '',
                    ])
            except Exception:
                pass

    def get_history(self, n: int = 50) -> list:
        if not os.path.exists(LOG_PATH):
            return []
        with self._lock:
            try:
                with open(LOG_PATH, 'r', newline='', encoding='utf-8') as f:
                    rows = list(csv.DictReader(f))
                return rows[-n:]
            except Exception:
                return []
