# Whisper Dict

Local speech-to-text dictation for Windows. Hold a hotkey, speak, release — transcription appears at your cursor.

Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (runs fully offline, no data leaves your machine).

## Quick Install

Open PowerShell **as your normal user** (not admin) and run:

```powershell
iex (iwr -UseBasicParsing https://raw.githubusercontent.com/cyeTeam/whisper-dict/master/install.ps1).Content
```

This downloads the repo, creates a Python virtual environment, installs dependencies, and runs the interactive setup wizard.

### Manual install

```powershell
git clone https://github.com/cyeTeam/whisper-dict.git
cd whisper-dict
python -m venv venv
venv\Scripts\pip install -r requirements.txt
python setup.py
```

## Usage

Hold the configured hotkey (default: `Ctrl+Alt+Space`) and speak. On release, speech is transcribed and pasted into the active window.

- **System tray** icon for enable/disable and status.
- **Overlay dot** (bottom-left): gray = idle, blue = recording, cyan = processing.
- **Transcription log** saved to `%APPDATA%\WhisperDict\history.csv`.

Run `python main.py` (or `whisper-dict` if installed via the launcher) to start the daemon.

## Configuration

Settings are in `%APPDATA%\WhisperDict\config.json`:

| Key | Default | Description |
|-----|---------|-------------|
| `hotkey` | `ctrl+alt+space` | Push-to-talk hotkey |
| `model_size` | `base` | Model: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `language` | `null` | Language code (`en`, `fr`, `de`, ...) or `null` for auto-detect |
| `device` | `auto` | Compute device: `auto`, `cpu`, `cuda` |
| `microphone_index` | `null` | Specific mic, or `null` for default |
| `silence_threshold` | `0.03` | Silence detection sensitivity |
| `startup_enabled` | `false` | Auto-start on login |
| `wake_word_mode` | `false` | Toggle wake-word activation |

## Updating

Re-run the install command. The app will also notify about new versions on startup.

```powershell
iex (iwr -UseBasicParsing https://raw.githubusercontent.com/cyeTeam/whisper-dict/master/install.ps1).Content
```
