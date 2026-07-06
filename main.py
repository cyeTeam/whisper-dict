import logging
import sys
import threading
import time
from enum import Enum
from typing import Optional

from config import load_config, save_config
from hotkey_listener import HotkeyListener
from audio_recorder import AudioRecorder
from whisper_engine import WhisperEngine
from clipboard_handler import ClipboardHandler
from transcription_logger import TranscriptionLogger
from tray_ui import TrayUI
from overlay_indicator import OverlayIndicator

_VERBOSE = '-v' in sys.argv or '--verbose' in sys.argv

logging.basicConfig(
    level=logging.DEBUG if _VERBOSE else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger('dictation')


class State(Enum):
    IDLE = 0
    RECORDING = 1
    TRANSCRIBING = 2


class WhisperDict:
    def __init__(self):
        self.config = load_config()
        self.enabled = True
        self._state = State.IDLE
        self._lock = threading.Lock()

        self.recorder = AudioRecorder(
            device_index=self.config.microphone_index,
            silence_threshold=self.config.silence_threshold,
        )
        self.engine = WhisperEngine(
            model_size=self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type,
            status_callback=self._on_engine_status,
        )
        self.clipboard = ClipboardHandler()
        self.logger = TranscriptionLogger(
            enabled=self.config.transcription_log_enabled,
            max_entries=self.config.max_log_entries,
        )

        self.hotkey = HotkeyListener(self.config.hotkey)
        self.hotkey.set_callbacks(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )

        self.tray: Optional[TrayUI] = None
        if self.config.tray_enabled:
            self.tray = TrayUI(self)

        self.overlay = OverlayIndicator()

    def _on_hotkey_press(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            if self._state != State.IDLE:
                return
            self._state = State.RECORDING
            self.overlay.set_listening()

        logger.info('Recording started')
        try:
            self.recorder.start_recording()
        except Exception as e:
            logger.error('Failed to start recording: %s', e)
            with self._lock:
                self._state = State.IDLE
                self.overlay.set_idle()

    def _on_hotkey_release(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            if self._state != State.RECORDING:
                return
            self._state = State.TRANSCRIBING
            self.overlay.set_processing()

        logger.info('Recording stopped')

        audio = self.recorder.stop_recording()
        if audio is None or len(audio) == 0:
            logger.warning('No audio captured')
            with self._lock:
                self._state = State.IDLE
                self.overlay.set_idle()
            return

        def transcribe_and_paste():
            try:
                self.engine.load_model()
                text = self.engine.transcribe(audio, language=self.config.language)
                logger.info('Transcribed: %s', text[:80] + ('...' if len(text) > 80 else ''))

                if text:
                    self.clipboard.paste_text(text)
                    duration = len(audio) / self.recorder.sample_rate
                    self.logger.log(text, duration)
                else:
                    logger.info('No speech detected')
            except Exception as e:
                logger.error('Transcription failed: %s', e, exc_info=True)
            finally:
                with self._lock:
                    self._state = State.IDLE
                self.overlay.set_idle()

        threading.Thread(target=transcribe_and_paste, daemon=True).start()

    def _on_engine_status(self, status: str) -> None:
        logger.info('Engine status: %s', status)
        if self.tray:
            self.tray.set_status(status)

    def start(self) -> None:
        logger.info('Starting Whisper Dict')
        logger.info('Hotkey: %s  Model: %s', self.config.hotkey, self.config.model_size)
        self.overlay.start()
        self.hotkey.start()
        if self.tray:
            t = threading.Thread(target=self.tray.run, daemon=True)
            t.start()

        logger.info('Whisper Dict is running. Hold %s to dictate.', self.config.hotkey)

        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self) -> None:
        logger.info('Shutting down')
        self.hotkey.stop()
        if self.recorder.is_recording():
            try:
                self.recorder.stop_recording()
            except Exception:
                pass
        if self.tray:
            self.tray.stop()
        self.overlay.stop()


if __name__ == '__main__':
    service = WhisperDict()
    service.start()
