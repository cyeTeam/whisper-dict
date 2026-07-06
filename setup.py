"""
Whisper Dict - Setup Wizard

Interactive CLI installer/configure for the local Whisper dictation service.
Install: iex (iwr -UseBasicParsing https://raw.githubusercontent.com/cyeTeam/whisper-dict/master/install.ps1).Content
"""

import os
import sys
import subprocess
import shutil
import json
import ctypes
import platform

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, 'venv')
CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'WhisperDict')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')
STARTUP_LNK = os.path.join(
    os.environ.get('APPDATA', ''),
    r'Microsoft\Windows\Start Menu\Programs\Startup\WhisperDict.lnk',
)

SEP = '-' * 60


def _clr():
    """Quick ANSI color helper (Windows 10+)."""
    class C:
        HEAD = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        DIM = '\033[2m'
        END = '\033[0m'
    return C


def _ensure_ansi():
    """Enable ANSI support on Windows."""
    if platform.system() == 'Windows':
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


def _print_banner():
    C = _clr()
    _ensure_ansi()
    print()
    print(f'{C.BOLD}{C.CYAN}+----------------------------------------------------+{C.END}')
    print(f'{C.BOLD}{C.CYAN}|             Whisper Dict - Setup Wizard             |{C.END}')
    print(f'{C.BOLD}{C.CYAN}|    Local Whisper STT - Push-To-Talk Anywhere        |{C.END}')
    print(f'{C.BOLD}{C.CYAN}+----------------------------------------------------+{C.END}')
    print(SEP)
    print(f'{C.DIM}Project: {PROJECT_DIR}{C.END}')
    print()


def _check_python():
    C = _clr()
    v = sys.version_info
    print(f'  Python {v.major}.{v.minor}.{v.micro}')
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print(f'  {C.RED}[FAIL] Python 3.8+ required{C.END}')
        return False
        print(f'  {C.GREEN}[OK] Python {v.major}.{v.minor}.{v.micro}{C.END}')
    return True


def _check_pip():
    C = _clr()
    try:
        import pip
        print(f'  {C.GREEN}[OK] pip {pip.__version__}{C.END}')
        return True
    except ImportError:
        print(f'  {C.RED}[FAIL] pip not found{C.END}')
        return False


def _install_deps(venv=False, quiet=False):
    C = _clr()
    req = os.path.join(PROJECT_DIR, 'requirements.txt')
    if not os.path.exists(req):
        print(f'  {C.RED}[FAIL] requirements.txt not found{C.END}')
        return False

    python = sys.executable
    if venv:
        venv_python = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
        if os.path.exists(venv_python):
            python = venv_python

    print(f'  Installing dependencies from requirements.txt ...')
    print(f'  {C.DIM}  This may take several minutes (torch is ~2-3 GB).{C.END}')
    if quiet:
        result = subprocess.run(
            [python, '-m', 'pip', 'install', '-r', req],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f'  {C.GREEN}[OK] Dependencies installed{C.END}')
            return True
        else:
            print(f'  {C.RED}[FAIL] pip install failed:{C.END}')
            for line in result.stderr.splitlines()[-5:]:
                print(f'    {C.DIM}{line}{C.END}')
            return False
    else:
        print(f'  {C.DIM}  (streaming pip output below){C.END}')
        print()
        result = subprocess.run(
            [python, '-m', 'pip', 'install', '-r', req],
            capture_output=False,
        )
        if result.returncode == 0:
            print(f'\n  {C.GREEN}[OK] Dependencies installed{C.END}')
            return True
        else:
            print(f'\n  {C.RED}[FAIL] pip install failed (exit code {result.returncode}){C.END}')
            return False


def _create_venv():
    C = _clr()
    if os.path.exists(VENV_DIR):
        print(f'  {C.YELLOW}[!] Virtual env already exists{C.END}')
        return True
    print('  Creating virtual environment ...')
    result = subprocess.run(
        [sys.executable, '-m', 'venv', VENV_DIR],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f'  {C.GREEN}[OK] Virtual env created{C.END}')
        return True
    else:
        print(f'  {C.RED}[FAIL] venv creation failed{C.END}')
        for line in result.stderr.splitlines()[-3:]:
            print(f'    {C.DIM}{line}{C.END}')
        return False


def _ensure_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        default = {
            'hotkey': 'ctrl+alt+space',
            'model_size': 'base',
            'device': 'auto',
            'compute_type': 'default',
            'microphone_index': None,
            'silence_threshold': 0.03,
            'min_record_duration': 0.3,
            'startup_enabled': False,
            'tray_enabled': True,
            'wake_word_mode': False,
            'wake_word': 'hey computer',
            'transcription_log_enabled': True,
            'max_log_entries': 1000,
            'language': None,
        }
        with open(CONFIG_PATH, 'w') as f:
            json.dump(default, f, indent=2)


def _load_config():
    _ensure_config()
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def _save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)


def _ask(question, default=None):
    """Ask yes/no question."""
    C = _clr()
    suffix = f' [{default}]' if default else ''
    while True:
        answer = input(f'  {C.BOLD}{question}{suffix}{C.END} ').strip().lower()
        if not answer and default:
            return default.lower() == 'y'
        if answer in ('y', 'yes', 'ye'):
            return True
        if answer in ('n', 'no'):
            return False
        print(f'  {C.YELLOW}Please answer y or n{C.END}')


def _prompt(question, default=None):
    C = _clr()
    suffix = f' [{default}]' if default else ''
    answer = input(f'  {C.BOLD}{question}{suffix}{C.END} ').strip()
    return answer if answer else (default or '')


def _list_microphones():
    """List available input devices using sounddevice heuristic."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        inputs = [(i, d) for i, d in enumerate(devices) if d['max_input_channels'] > 0]
        return inputs
    except ImportError:
        return None


def _select_microphone(cfg):
    C = _clr()
    print(f'\n{SEP}')
    print(f'  {C.BOLD}Microphone Selection{C.END}')
    print()
    inputs = _list_microphones()
    if inputs is None:
        print(f'  {C.YELLOW}[!] Cannot list devices - sounddevice not installed yet{C.END}')
        print(f'  {C.DIM}  (You can run setup again after installing deps){C.END}')
        return cfg
    if not inputs:
        print(f'  {C.RED}[FAIL] No input devices found!{C.END}')
        return cfg
    print(f'  Available microphones:')
    for i, (idx, dev) in enumerate(inputs):
        default_mark = ' (default)' if dev.get('default_samplerate') else ''
        print(f'    [{i}] {dev["name"]}{default_mark}')
    print()
    choice = input(f'  Select microphone [0-{len(inputs)-1}] or Enter for default: ').strip()
    if choice.isdigit() and 0 <= int(choice) < len(inputs):
        cfg['microphone_index'] = inputs[int(choice)][0]
        print(f'  {C.GREEN}[OK] Selected: {inputs[int(choice)][1]["name"]}{C.END}')
    else:
        cfg['microphone_index'] = None
        print(f'  {C.GREEN}[OK] Using system default{C.END}')
    return cfg


def _select_model(cfg):
    C = _clr()
    models = ['tiny', 'base', 'small', 'medium', 'large-v3']
    print()
    print(f'  {C.BOLD}Whisper Model Selection{C.END}')
    print(f'  {C.DIM}  bigger  -> more accurate, slower, more RAM{C.END}')
    print(f'  {C.DIM}  smaller -> faster, less accurate, less RAM{C.END}')
    print()
    for i, m in enumerate(models):
        sz = {'tiny': '~75 MB  (1 GB RAM)', 'base': '~150 MB  (1 GB RAM)',
              'small': '~500 MB  (2 GB RAM)', 'medium': '~1.5 GB  (5 GB RAM)',
              'large-v3': '~3 GB  (10 GB RAM)'}
        note = sz.get(m, '')
        mark = ' <- recommended' if m == 'base' else ''
        print(f'    [{i}] {m:<12} {note}{mark}')
    print()
    default_idx = models.index('base')
    choice = input(f'  Select model [0-{len(models)-1}] (default: {default_idx}): ').strip()
    if choice.isdigit() and 0 <= int(choice) < len(models):
        cfg['model_size'] = models[int(choice)]
    else:
        cfg['model_size'] = 'base'
        print(f'  {C.GREEN}[OK] Model: {cfg["model_size"]}{C.END}')
    return cfg


def _select_hotkey(cfg):
    C = _clr()
    print()
    print(f'  {C.BOLD}Hotkey Configuration{C.END}')
    print(f'  {C.DIM}  Format: ctrl+alt+space, ctrl+shift+h, alt+`{C.END}')
    print(f'  {C.DIM}  Keys separated by +{C.END}')
    hotkey = input(f'  Hotkey [ctrl+alt+space]: ').strip().lower()
    if hotkey:
        cfg['hotkey'] = hotkey
    else:
        cfg['hotkey'] = 'ctrl+alt+space'
        print(f'  {C.GREEN}[OK] Hotkey: {cfg["hotkey"]}{C.END}')
    return cfg


def _configure_language(cfg):
    C = _clr()
    print()
    print(f'  {C.BOLD}Language{C.END}')
    print(f'  {C.DIM}  Enter language code (en, fr, de, ja, zh, etc.) or leave empty for auto-detect{C.END}')
    lang = input(f'  Language [auto]: ').strip().lower()
    cfg['language'] = lang if lang else None
    if cfg['language']:
        print(f'  {C.GREEN}[OK] Language: {cfg["language"]}{C.END}')
    else:
        print(f'  {C.GREEN}[OK] Auto-detect{C.END}')
    return cfg


def _setup_startup(cfg):
    C = _clr()
    print()
    print(f'  {C.BOLD}Auto-Start{C.END}')
    print(f'  {C.DIM}  Launch Whisper Dict when you log in{C.END}')
    if _ask('Add to Windows startup?', 'n'):
        cfg['startup_enabled'] = _create_startup_shortcut()
    else:
        cfg['startup_enabled'] = False
        _remove_startup_shortcut()
    status = 'enabled' if cfg['startup_enabled'] else 'disabled'
    print(f'  {C.GREEN}[OK] Startup: {status}{C.END}')
    return cfg


def _create_startup_shortcut():
    """Create Windows startup shortcut using PowerShell."""
    C = _clr()
    try:
        ps_code = '''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("%s")
$s.TargetPath = "%s"
$s.WorkingDirectory = "%s"
$s.Description = "Whisper Dict - Local Whisper STT"
$s.Save()
        '''.replace('\n', '; ').replace('    ', '')
        ps_code = ps_code.strip().rstrip(';').replace('    ', '')

        target = os.path.join(PROJECT_DIR, 'venv', 'Scripts', 'pythonw.exe')
        if not os.path.exists(target):
            target = sys.executable.replace('python.exe', 'pythonw.exe')
            if not os.path.exists(target):
                target = sys.executable

        script_path = STARTUP_LNK

        cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{script_path}"); '
            f'$s.TargetPath = "{target}"; '
            f'$s.Arguments = "{os.path.join(PROJECT_DIR, "main.py")}"; '
            f'$s.WorkingDirectory = "{PROJECT_DIR}"; '
            f'$s.Description = "Whisper Dict"; '
            f'$s.Save()'
        )
        result = subprocess.run(['powershell', '-Command', cmd], capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(script_path):
            print(f'  {C.GREEN}[OK] Startup shortcut created{C.END}')
            return True
        else:
            print(f'  {C.YELLOW}[!] Could not create startup shortcut{C.END}')
            if result.stderr.strip():
                print(f'  {C.DIM}    {result.stderr.strip()}{C.END}')
            return False
    except Exception as e:
        print(f'  {C.YELLOW}[!] Startup shortcut failed: {e}{C.END}')
        return False


def _remove_startup_shortcut():
    if os.path.exists(STARTUP_LNK):
        try:
            os.remove(STARTUP_LNK)
        except Exception:
            pass


def _test_recording():
    C = _clr()
    print(f'\n{SEP}')
    print(f'  {C.BOLD}Microphone Test{C.END}')
    print()
    if not _ask('Test microphone (record 3 seconds)?', 'y'):
        return True
    try:
        import sounddevice as sd
        import numpy as np
        duration = 3
        fs = 16000
        print(f'  Recording {duration}s ... (speak now)')
        audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
        sd.wait()
        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.max(np.abs(audio))
        print(f'  RMS: {rms:.4f}  Peak: {peak:.4f}')
        if peak > 0.02:
            print(f'  {C.GREEN}[OK] Microphone working (signal detected){C.END}')
        else:
            print(f'  {C.YELLOW}[!] Very quiet - check mic gain/position{C.END}')
        print(f'  {C.DIM}  (Press Enter to continue){C.END}')
        input()
        return True
    except Exception as e:
        print(f'  {C.RED}[FAIL] Mic test failed: {e}{C.END}')
        return False


def _summary(cfg):
    C = _clr()
    print(f'\n{SEP}')
    print(f'  {C.BOLD}{C.GREEN}Setup Complete!{C.END}')
    print(f'{SEP}')
    print()
    print(f'  {C.BOLD}Configuration:{C.END}')
    print(f'    Hotkey:      {C.CYAN}{cfg["hotkey"]}{C.END}')
    print(f'    Model:       {C.CYAN}{cfg["model_size"]}{C.END}')
    print(f'    Language:    {C.CYAN}{cfg["language"] or "auto-detect"}{C.END}')
    print(f'    Mic:         {C.CYAN}{cfg["microphone_index"] if cfg["microphone_index"] is not None else "default"}{C.END}')
    print(f'    Startup:     {C.CYAN}{"enabled" if cfg["startup_enabled"] else "disabled"}{C.END}')
    print(f'    Device:      {C.CYAN}{cfg["device"]}{C.END}')
    print()
    print(f'  {C.BOLD}Launch:{C.END}')
    venv_python = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    if os.path.exists(venv_python):
        print(f'    {VENV_DIR}\\Scripts\\python main.py')
    else:
        print(f'    python main.py')
    print()
    print(f'  {C.DIM}  First run will download the Whisper model (~{_model_size_mb(cfg["model_size"])} MB).{C.END}')
    print(f'  {C.DIM}  Config file: {CONFIG_PATH}{C.END}')
    print(f'  {C.DIM}  Log file:    {os.path.join(CONFIG_DIR, "history.csv")}{C.END}')
    print()
    if _ask('Launch the service now?', 'y'):
        _launch_service()


def _model_size_mb(model):
    sizes = {'tiny': 75, 'base': 150, 'small': 500, 'medium': 1500, 'large-v3': 3000}
    return sizes.get(model, 150)


def _launch_service():
    C = _clr()
    print(f'  Launching Whisper Dict ...')
    venv_python = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    python = venv_python if os.path.exists(venv_python) else sys.executable
    main_py = os.path.join(PROJECT_DIR, 'main.py')
    try:
        subprocess.Popen(
            [python, main_py],
            cwd=PROJECT_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f'  {C.GREEN}[OK] Service launched in background{C.END}')
    except Exception as e:
        print(f'  {C.RED}[FAIL] Launch failed: {e}{C.END}')


def _config_exists() -> bool:
    return os.path.exists(CONFIG_PATH)


def _factory_reset() -> None:
    """Wipe APPDATA config/history and model cache."""
    C = _clr()
    wiped = []

    if os.path.exists(CONFIG_DIR):
        try:
            import shutil
            shutil.rmtree(CONFIG_DIR, ignore_errors=True)
            wiped.append(f'Config: {CONFIG_DIR}')
        except Exception as e:
            print(f'  {C.YELLOW}[!] Could not wipe config: {e}{C.END}')

    cache_dirs = [
        os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub'),
        os.path.join(os.path.expanduser('~'), '.cache', 'ctranslate2'),
    ]
    for d in cache_dirs:
        if os.path.exists(d):
            for entry in os.listdir(d):
                if 'faster-whisper' in entry or 'Systran' in entry or 'ctranslate2' in entry.lower():
                    path = os.path.join(d, entry)
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                        else:
                            import shutil
                            shutil.rmtree(path, ignore_errors=True)
                        wiped.append(f'Cache: {path}')
                    except Exception:
                        pass

    lnk = STARTUP_LNK
    if os.path.exists(lnk):
        try:
            os.remove(lnk)
            wiped.append(f'Startup: {lnk}')
        except Exception:
            pass

    for w in wiped:
        print(f'  {C.DIM}  Removed: {w}{C.END}')
    if wiped:
        print(f'  {C.GREEN}[OK] Factory reset complete{C.END}')
    else:
        print(f'  {C.YELLOW}[!] Nothing to reset{C.END}')


def _parse_args():
    flags = {
        'factory_reset': '--factory-reset' in sys.argv,
        'download_model': '--download-model' in sys.argv,
        'verbose': '-v' in sys.argv or '--verbose' in sys.argv,
        'quiet': '-q' in sys.argv or '--quiet' in sys.argv,
    }
    return flags


def _download_model(model=None):
    """Pre-download the Whisper model with visible progress."""
    C = _clr()

    if model is None:
        _ensure_config()
        cfg = _load_config()
        model = cfg.get('model_size', 'base')

    print(f'\n{SEP}')
    print(f'  {C.BOLD}Model Download{C.END}')
    print()

    repo_ids = {
        'tiny': 'Systran/faster-whisper-tiny',
        'base': 'Systran/faster-whisper-base',
        'small': 'Systran/faster-whisper-small',
        'medium': 'Systran/faster-whisper-medium',
        'large-v3': 'Systran/faster-whisper-large-v3',
    }
    repo = repo_ids.get(model, f'Systran/faster-whisper-{model}')
    cache = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')

    print(f'  Downloading {model} model ({repo}) ...')
    print(f'  {C.DIM}  (huggingface_hub progress bars below, may take a few min){C.END}')
    print()

    try:
        from huggingface_hub import snapshot_download
        local_path = snapshot_download(
            repo,
            cache_dir=cache,
            resume_download=True,
            local_files_only=False,
        )
        print(f'\n  {C.GREEN}[OK] Model downloaded to:{C.END}')
        print(f'  {C.DIM}    {local_path}{C.END}')
    except ImportError:
        print(f'  {C.RED}[FAIL] huggingface-hub not installed. Run setup first.{C.END}')
        sys.exit(1)
    except Exception as e:
        print(f'  {C.RED}[FAIL] Download failed: {e}{C.END}')
        sys.exit(1)


def _quick_install():
    """Non-interactive default install for automation."""
    C = _clr()
    print('  Running quick default install ...')
    _ensure_config()
    cfg = _load_config()
    _save_config(cfg)
    print(f'  {C.GREEN}[OK] Config initialized{C.END}')
    return cfg


def main():
    C = _clr()
    flags = _parse_args()

    if flags['factory_reset']:
        print(f'\n  {C.BOLD}Factory Reset{C.END}')
        _factory_reset()
        sys.exit(0)

    if flags['download_model']:
        _download_model()
        sys.exit(0)

    _print_banner()

    print(f'  {C.BOLD}System Check{C.END}')
    ok = _check_python()
    ok &= _check_pip()
    if not ok:
        print(f'\n  {C.RED}System requirements not met. Exiting.{C.END}')
        sys.exit(1)

    if _config_exists():
        print()
        print(f'  {C.YELLOW}[!] Existing configuration detected{C.END}')
        print(f'  {C.DIM}    {CONFIG_PATH}{C.END}')
        if _ask('Factory reset (wipe config, history, model cache)?', 'n'):
            _factory_reset()
            print()
        elif _ask('Keep existing config and reconfigure?', 'y'):
            print(f'  {C.DIM}  Keeping config{C.END}')
        else:
            print(f'  {C.DIM}  Using existing config as-is{C.END}')

    print(f'\n{SEP}')
    print(f'  {C.BOLD}Dependency Installation{C.END}')
    print()
    use_venv = _ask('Create virtual environment (recommended)?', 'y')
    if use_venv:
        _create_venv()
    _install_deps(venv=use_venv, quiet=flags['quiet'])

    _ensure_config()
    cfg = _load_config()

    print(f'\n{SEP}')
    print(f'  {C.BOLD}Configuration Wizard{C.END}')
    print()
    if _ask('Configure settings now?', 'y'):
        cfg = _select_hotkey(cfg)
        cfg = _select_model(cfg)
        if _ask('Download Whisper model now (avoids delay on first use)?', 'y'):
            _download_model(cfg['model_size'])
        cfg = _configure_language(cfg)
        cfg = _select_microphone(cfg)
        cfg = _setup_startup(cfg)
        _save_config(cfg)
    else:
        cfg = _quick_install()

    _test_recording()
    _summary(cfg)

    print(f'\n{SEP}')
    print(f'  {C.DIM}Setup complete. Press Enter to exit.{C.END}')
    print()
    try:
        input()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
