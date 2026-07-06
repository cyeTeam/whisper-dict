import time
import threading
import logging

import pyperclip
import keyboard

logger = logging.getLogger('dictation.clipboard')


class ClipboardHandler:
    def __init__(self):
        self._original = ''

    def paste_text(self, text: str) -> None:
        try:
            self._original = pyperclip.paste()
        except Exception:
            self._original = ''

        pyperclip.copy(text)
        time.sleep(0.05)

        keyboard.send('ctrl+v')

        def restore():
            time.sleep(0.15)
            try:
                pyperclip.copy(self._original)
            except Exception:
                pass

        threading.Thread(target=restore, daemon=True).start()
