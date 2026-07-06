import json
import os
from dataclasses import dataclass, asdict, field
from typing import Optional

CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'WhisperDict')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')


@dataclass
class Config:
    hotkey: str = 'ctrl+alt+space'
    model_size: str = 'base'
    device: str = 'auto'
    compute_type: str = 'default'
    microphone_index: Optional[int] = None
    silence_threshold: float = 0.03
    min_record_duration: float = 0.3
    startup_enabled: bool = False
    tray_enabled: bool = True
    wake_word_mode: bool = False
    wake_word: str = 'hey computer'
    transcription_log_enabled: bool = True
    max_log_entries: int = 1000
    language: Optional[str] = None


def load_config() -> Config:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return Config()


def save_config(config: Config) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=2)
