import time
import threading
import ctypes
import logging

import pyperclip

logger = logging.getLogger('dictation.clipboard')

VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

user32 = ctypes.windll.user32


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', ctypes.c_ushort),
        ('wScan', ctypes.c_ushort),
        ('dwFlags', ctypes.c_ulong),
        ('time', ctypes.c_ulong),
        ('dwExtraInfo', ctypes.c_void_p),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ('type', ctypes.c_ulong),
        ('ki', _KEYBDINPUT),
    ]


def _send_ctrl_v():
    inputs = (_INPUT * 4)()
    inputs[0] = _INPUT(INPUT_KEYBOARD, _KEYBDINPUT(VK_CONTROL, 0, 0, 0, None))
    inputs[1] = _INPUT(INPUT_KEYBOARD, _KEYBDINPUT(VK_V, 0, 0, 0, None))
    inputs[2] = _INPUT(INPUT_KEYBOARD, _KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, None))
    inputs[3] = _INPUT(INPUT_KEYBOARD, _KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, None))
    user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(_INPUT))


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

        _send_ctrl_v()

        def restore():
            time.sleep(0.15)
            try:
                pyperclip.copy(self._original)
            except Exception:
                pass

        threading.Thread(target=restore, daemon=True).start()
