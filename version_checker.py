import os
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger('dictation.version')

VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')
UPDATE_URL = 'https://api.github.com/repos/cyeTeam/whisper-dict/commits/master'
CHECK_INTERVAL = timedelta(hours=24)


def _read_local_commit() -> Optional[str]:
    try:
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    except Exception:
        return None


def _fetch_latest_commit() -> Optional[str]:
    try:
        req = Request(UPDATE_URL, headers={'User-Agent': 'whisper-dict', 'Accept': 'application/vnd.github.v3+json'})
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        return data.get('sha')
    except (URLError, json.JSONDecodeError, OSError):
        return None


def _state_path() -> str:
    data_dir = os.environ.get('APPDATA', os.path.expanduser('~'))
    return os.path.join(data_dir, 'WhisperDict', '.update_check')


def _should_check() -> bool:
    path = _state_path()
    try:
        mtime = os.path.getmtime(path)
        last = datetime.fromtimestamp(mtime)
        return datetime.now() - last > CHECK_INTERVAL
    except OSError:
        return True


def _mark_checked():
    path = _state_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write('')
    except OSError:
        pass


def check_update_async():
    threading.Thread(target=_check_update, daemon=True).start()


def _check_update():
    local = _read_local_commit()
    if not local:
        return

    if not _should_check():
        return

    _mark_checked()
    latest = _fetch_latest_commit()
    if not latest:
        return

    if latest != local:
        short_local = local[:7]
        short_latest = latest[:7]
        logger.warning(
            'Update available: %s -> %s. '
            'Run: iex (iwr -UseBasicParsing https://raw.githubusercontent.com/cyeTeam/whisper-dict/master/install.ps1).Content',
            short_local, short_latest,
        )
        print(
            f'\n  [Update] New version available ({short_local} -> {short_latest}).\n'
            f'  Run the installer again to update:\n'
            f'    iex (iwr -UseBasicParsing https://raw.githubusercontent.com/cyeTeam/whisper-dict/master/install.ps1).Content\n'
        )
