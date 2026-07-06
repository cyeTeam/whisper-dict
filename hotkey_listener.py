import threading
from typing import Callable, Optional, Set

import keyboard


_NAME_MAP = {
    'left ctrl': 'ctrl', 'right ctrl': 'ctrl',
    'left alt': 'alt', 'right alt': 'alt',
    'left shift': 'shift', 'right shift': 'shift',
    'ctrl': 'ctrl', 'alt': 'alt', 'shift': 'shift',
}


class HotkeyListener:
    def __init__(self, combo: str):
        self._combo_keys = [k.strip().lower() for k in combo.replace('  ', ' ').split('+')]
        self._on_press: Optional[Callable] = None
        self._on_release: Optional[Callable] = None
        self._active = False
        self._pressed: Set[str] = set()
        self._hook: Optional[object] = None
        self._lock = threading.Lock()

    def set_callbacks(self, on_press: Callable, on_release: Callable) -> None:
        self._on_press = on_press
        self._on_release = on_release

    def start(self) -> None:
        self._hook = keyboard.hook(self._handle)

    def stop(self) -> None:
        if self._hook:
            keyboard.unhook(self._hook)
            self._hook = None

    @staticmethod
    def _normalize(name: str) -> str:
        return _NAME_MAP.get(name, name)

    def _handle(self, event) -> None:
        name = self._normalize(event.name.lower())

        if event.event_type == 'down':
            self._pressed.add(name)
            if not self._active:
                if all(k in self._pressed for k in self._combo_keys):
                    self._active = True
                    if self._on_press:
                        threading.Thread(target=self._on_press, daemon=True).start()

        elif event.event_type == 'up':
            self._pressed.discard(name)
            if self._active:
                if not all(k in self._pressed for k in self._combo_keys):
                    self._active = False
                    if self._on_release:
                        threading.Thread(target=self._on_release, daemon=True).start()
