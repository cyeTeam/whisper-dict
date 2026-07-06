import os
import threading
import logging
from typing import TYPE_CHECKING, Optional

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger('dictation.tray')

if TYPE_CHECKING:
    from main import WhisperDict

ICON_SIZE = 64
COLOR_IDLE = (100, 150, 255)
COLOR_RECORDING = (255, 60, 60)
COLOR_DISABLED = (120, 120, 120)


def _make_icon(color, size=ICON_SIZE):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size * 0.35

    draw.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.4], fill=color)
    rx = r * 0.35
    ry = r * 0.3
    draw.rectangle([cx - rx, cy + r * 0.35, cx + rx, cy + r * 1.1], fill=color)
    draw.rectangle([cx - r * 0.5, cy + r * 0.9, cx + r * 0.5, cy + r * 1.2], fill=color)
    draw.rectangle([cx - rx * 0.5, cy + r * 1.1, cx + rx * 0.5, cy + r * 1.35], fill=color)

    return img


class TrayUI:
    def __init__(self, service: 'WhisperDict'):
        self.service = service
        self._icon: Optional[pystray.Icon] = None
        self._menu_lock = threading.Lock()

    def run(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem('Enable Whisper Dict', self._toggle_enabled, checked=lambda _: self.service.enabled),
            pystray.MenuItem('Status: Idle', None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Settings', self._open_settings),
            pystray.MenuItem('Open Log', self._open_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit', self._exit),
        )

        icon_img = _make_icon(COLOR_IDLE)
        self._icon = pystray.Icon(
            'whisper_dict',
            icon_img,
            'Whisper Dict',
            menu,
        )
        self._icon.run()

    def set_tooltip(self, text: str) -> None:
        if self._icon:
            self._icon.title = text
            self._icon.update_menu()

    def set_status(self, text: str) -> None:
        if self._icon:
            self._icon.title = f'Whisper Dict — {text}'
            self._icon.update_menu()

    def update_status(self, recording: bool) -> None:
        if self._icon:
            color = COLOR_RECORDING if recording else COLOR_IDLE
            icon_img = _make_icon(color)
            self._icon.icon = icon_img
            self._icon.title = 'Recording...' if recording else 'Whisper Dict'
            self._icon.update_menu()

    def _toggle_enabled(self) -> None:
        self.service.enabled = not self.service.enabled
        if self._icon:
            color = COLOR_DISABLED if not self.service.enabled else COLOR_IDLE
            self._icon.icon = _make_icon(color)

    def _open_settings(self) -> None:
        logger.info('Settings requested (not implemented in tray)')

    def _open_log(self) -> None:
        log_path = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'WhisperDict', 'history.csv',
        )
        if os.path.exists(log_path):
            os.startfile(log_path)

    def _exit(self) -> None:
        if self._icon:
            self._icon.stop()
        self.service.stop()
        os._exit(0)

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
