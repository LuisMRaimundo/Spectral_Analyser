# SoundSpectrAnalyse — macOS installation

**Repository:** https://github.com/LuisMRaimundo/SoundSpectrAnalyse

**Note:** scripts in this folder must run **on a Mac**. You cannot build or install the `.app` from Windows.

---

## Standard installation (no prior Python required)

### Requirements

- **macOS 11 (Big Sur)** or later
- **Intel** or **Apple Silicon (M1/M2/M3)**
- **Internet** connection (first install)
- Standard user account (install under `~/Applications`)

### Step-by-step

1. **Obtain the installer files**
   - On the Mac, clone the repository or download the GitHub ZIP and open **`instalers/mac`**.

2. **Open Terminal**
   - **Finder → Applications → Utilities → Terminal**.

3. **Go to the installer folder**
   ```bash
   cd ~/Desktop/instalers/mac
   ```
   Adjust the path if you placed the folder elsewhere.

4. **Make the script executable**
   ```bash
   chmod +x install-easy.sh
   ```

5. **Run installation**
   ```bash
   ./install-easy.sh
   ```
   - If Python 3.10/3.11 is missing, the script tries **Homebrew** (`brew install python@3.11`). Without Homebrew, install Python from https://www.python.org/downloads/ and repeat step 5.
   - The script downloads the project from GitHub and installs dependencies — **10–25 minutes** on first run.

6. **Launch the application**
   - **Finder → Applications → SoundSpectrAnalyse** → double-click **`Launch-SoundSpectrAnalyse.command`**, or
   - Desktop: **`SoundSpectrAnalyse Orchestrator.command`**.

7. **Gatekeeper (first launch)**
   - If macOS blocks an unidentified developer:
     - **System Settings → Privacy & Security → Open Anyway**, or
     - Right-click the `.command` file → **Open** → **Open**.

### Install location

| Item | Path |
|------|------|
| Application code | `~/Applications/SoundSpectrAnalyse/app/` |
| Python environment | `~/Applications/SoundSpectrAnalyse/venv/` |
| Launcher script | `~/Applications/SoundSpectrAnalyse/Launch-SoundSpectrAnalyse.command` |

### Uninstall

```bash
rm -rf ~/Applications/SoundSpectrAnalyse
rm -f ~/Desktop/SoundSpectrAnalyse\ Orchestrator.command
```

Python installed via Homebrew or python.org is **not** removed.

### Audio and FFmpeg (optional)

For some formats (e.g. MP3):

```bash
brew install ffmpeg
```

Requires [Homebrew](https://brew.sh).

### Troubleshooting

| Issue | Action |
|-------|--------|
| `command not found: python3` | Install Python 3.11 from https://www.python.org/downloads/ or `brew install python@3.11`. |
| `tkinter` error | Reinstall Python from the official installer (includes Tcl/Tk). |
| Network / pip error | Check Wi‑Fi and proxy; run `./install-easy.sh` again. |
| Homebrew missing | Install from https://brew.sh or use python.org. |

---

## Portable `.app` (PyInstaller) — developers

For developers with the project Python environment already configured.

```bash
cd ~/Desktop/instalers/mac
chmod +x *.sh
./build-all.sh
```

| Output (local `output/`, not in Git) | Description |
|--------------------------------------|-------------|
| `output/app/SoundSpectrAnalyse.app` | Application bundle |
| `output/SoundSpectrAnalyse-macOS-3.7.0.zip` | Zip for distribution |
| `output/SoundSpectrAnalyse-macOS-3.7.0.dmg` | Disk image (drag to Applications) |

After `./build-pyinstaller.sh`, from `output/app/`:

```bash
./install-soundspectranalyse.sh
```

(or drag `SoundSpectrAnalyse.app` to **Applications**).

Unsigned applications may require extra steps under **Privacy & Security** (see above).
