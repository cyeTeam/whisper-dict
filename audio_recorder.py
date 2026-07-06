import threading
import logging
from typing import Optional, List

import numpy as np
import sounddevice as sd

logger = logging.getLogger('dictation.audio')


class AudioRecorder:
    def __init__(self, device_index: Optional[int] = None,
                 sample_rate: int = 16000,
                 silence_threshold: float = 0.03):
        self.device_index = device_index
        self.target_sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.sample_rate = sample_rate
        self._recording = False
        self._stream: Optional[sd.InputStream] = None
        self._buffer: List[np.ndarray] = []
        self._lock = threading.Lock()

    @staticmethod
    def list_devices():
        return sd.query_devices()

    @staticmethod
    def list_input_devices():
        devices = sd.query_devices()
        return [(i, d) for i, d in enumerate(devices) if d['max_input_channels'] > 0]

    @staticmethod
    def default_input_device():
        try:
            devices = sd.query_devices()
            default = sd.default.device
            if isinstance(default, tuple):
                idx = default[0]
            else:
                idx = default
            if idx is None or idx < 0:
                for i, d in enumerate(devices):
                    if d['max_input_channels'] > 0:
                        return i, d
                return None, None
            return idx, devices[idx]
        except Exception:
            return None, None

    def start_recording(self) -> bool:
        if self._recording:
            return False
        self._recording = True
        self._buffer = []

        def callback(indata, frames, time_info, status):
            if status:
                logger.debug('Stream status: %s', status)
            if self._recording:
                with self._lock:
                    self._buffer.append(indata.copy())

        dev = self.device_index
        sr = self.target_sample_rate

        try:
            if dev is not None:
                info = sd.query_devices(dev)
                logger.debug('Using device %d: %s (%.0f Hz)', dev, info['name'], sr)
            else:
                idx, info = self.default_input_device()
                if info:
                    logger.debug('Using default device %d: %s', idx, info['name'])

            self._stream = sd.InputStream(
                device=dev,
                channels=1,
                samplerate=sr,
                callback=callback,
                dtype='float32',
                blocksize=1024,
            )
            self._stream.start()
            self.sample_rate = sr
            return True

        except Exception as first_err:
            logger.warning('Failed with sample rate %d: %s', sr, first_err)

            try:
                if dev is None:
                    idx, info = self.default_input_device()
                    if info:
                        dev = idx
                        sr = int(info.get('default_samplerate', sr))
                        logger.info('Falling back to device %d at %.0f Hz', dev, sr)

                if dev is not None:
                    info = sd.query_devices(dev)
                    sr = int(info.get('default_samplerate', sr))

                logger.info('Retrying with device=%s rate=%d', dev, sr)
                self._stream = sd.InputStream(
                    device=dev,
                    channels=1,
                    samplerate=sr,
                    callback=callback,
                    dtype='float32',
                    blocksize=1024,
                )
                self._stream.start()
                self.sample_rate = sr
                return True

            except Exception as fallback_err:
                self._recording = False
                self._buffer = []
                logger.error('Microphone failed (device=%s, rate=%d): %s',
                             dev, sr, fallback_err)
                raise

    def stop_recording(self) -> Optional[np.ndarray]:
        if not self._recording:
            return None
        self._recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        with self._lock:
            if not self._buffer:
                return None
            audio = np.concatenate(self._buffer, axis=0).flatten()

        audio = self._trim_silence(audio)
        return audio

    def _trim_silence(self, audio: np.ndarray) -> np.ndarray:
        if len(audio) == 0:
            return audio
        threshold = self.silence_threshold
        mask = np.abs(audio) > threshold
        if not np.any(mask):
            return audio
        start = int(np.argmax(mask))
        end = int(len(audio) - np.argmax(mask[::-1]))
        return audio[start:end]

    def is_recording(self) -> bool:
        return self._recording
