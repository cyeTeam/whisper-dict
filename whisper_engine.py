import os
import threading
import logging
from typing import Optional, Callable

import numpy as np
import torch

from huggingface_hub import snapshot_download
from faster_whisper import WhisperModel

logger = logging.getLogger('dictation.whisper')

_MODEL_REPOS = {
    'tiny': 'Systran/faster-whisper-tiny',
    'base': 'Systran/faster-whisper-base',
    'small': 'Systran/faster-whisper-small',
    'medium': 'Systran/faster-whisper-medium',
    'large-v3': 'Systran/faster-whisper-large-v3',
}


def detect_device() -> str:
    if torch.cuda.is_available():
        return 'cuda'
    return 'cpu'


def resolve_compute_type(device: str, preferred: str) -> str:
    if preferred != 'default':
        return preferred
    if device == 'cuda':
        return 'float16'
    return 'int8'


def _default_cache_dir() -> str:
    return os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')


def _model_repo(model_size: str) -> str:
    return _MODEL_REPOS.get(model_size, f'Systran/faster-whisper-{model_size}')


def _is_model_cached(repo_id: str, cache_dir: str) -> bool:
    try:
        snapshot_download(repo_id, cache_dir=cache_dir, local_files_only=True, token=False)
        return True
    except Exception:
        return False


class WhisperEngine:
    def __init__(self, model_size: str = 'base',
                 device: str = 'auto',
                 compute_type: str = 'default',
                 model_dir: Optional[str] = None,
                 status_callback: Optional[Callable[[str], None]] = None):
        self.model_size = model_size
        self._device = device
        self.compute_type = compute_type
        self.model_dir = model_dir
        self._status_callback = status_callback or (lambda s: None)
        self._model: Optional[WhisperModel] = None
        self._lock = threading.Lock()

    @property
    def device(self) -> str:
        return detect_device() if self._device == 'auto' else self._device

    def is_loaded(self) -> bool:
        return self._model is not None

    def _report(self, status: str) -> None:
        logger.info('%s', status)
        self._status_callback(status)

    def load_model(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return

            dev = self.device
            ct = resolve_compute_type(dev, self.compute_type)

            repo_id = _model_repo(self.model_size)
            cache_dir = self.model_dir or _default_cache_dir()

            if not _is_model_cached(repo_id, cache_dir):
                self._report(
                    f'Downloading Whisper {self.model_size} model '
                    f'(~{_model_size_mb(self.model_size)} MB) ...'
                )
                local_path = snapshot_download(
                    repo_id,
                    cache_dir=cache_dir,
                    resume_download=True,
                    local_files_only=False,
                )
            else:
                self._report(f'Loading Whisper {self.model_size} from cache ...')
                local_path = snapshot_download(
                    repo_id,
                    cache_dir=cache_dir,
                    local_files_only=True,
                )

            self._report(f'Loading model on {dev} (compute_type={ct}) ...')
            self._model = WhisperModel(
                local_path,
                device=dev,
                compute_type=ct,
            )
            self._report('Ready')

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> str:
        if self._model is None:
            self.load_model()

        segments, _ = self._model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=200,
                threshold=0.5,
            ),
        )

        parts = [seg.text for seg in segments]
        return ' '.join(parts).strip()


def _model_size_mb(model: str) -> int:
    sizes = {'tiny': 75, 'base': 150, 'small': 500, 'medium': 1500, 'large-v3': 3000}
    return sizes.get(model, 150)
