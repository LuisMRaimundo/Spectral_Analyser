# SoundSpectrAnalyse — Linux installation

**Repository:** https://github.com/LuisMRaimundo/SoundSpectrAnalyse

**Note:** run these scripts **on Linux** (not on Windows or macOS).

---

## Standard installation (no prior Python required)

### Requirements

- **glibc**-based distribution (e.g. **Ubuntu 22.04+**, Debian 12, Fedora 38+, Linux Mint)
- **x86_64** (64-bit) recommended; other architectures may require installing from source
- **Internet** connection
- Graphical session (X11 or Wayland) for the Tk GUI

### Step-by-step (Ubuntu / Debian)

1. **System packages** (once; administrator password):
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip curl unzip
   sudo apt install -y python3-tk
   ```
   **`python3-tk`** is required for the graphical interface.

2. **Obtain the installer files**
   - Clone the repository or extract the GitHub ZIP and open **`instalers/linux`**.

3. **Terminal in the installer folder**
   ```bash
   cd ~/Desktop/instalers/linux
   ```
   Adjust the path as needed.

4. **Run installation**
   ```bash
   chmod +x install-easy.sh
   ./install-easy.sh
   ```
   - Downloads code from https://github.com/LuisMRaimundo/SoundSpectrAnalyse
   - Creates a virtual environment and installs libraries — **10–25 minutes** on first run.

5. **Launch the application**
   - Application menu: **SoundSpectrAnalyse Orchestrator**, or
   - Terminal:
     ```bash
     soundspectranalyse-gui
     ```

### Step-by-step (Fedora)

```bash
sudo dnf install -y python3 python3-pip python3-tkinter curl unzip
cd ~/Desktop/instalers/linux
chmod +x install-easy.sh
./install-easy.sh
```

### Install location

| Item | Path |
|------|------|
| Application code | `~/.local/share/SoundSpectrAnalyse/app/` |
| Python environment | `~/.local/share/SoundSpectrAnalyse/venv/` |
| Terminal command | `~/.local/bin/soundspectranalyse-gui` |
| Menu entry | `~/.local/share/applications/soundspectranalyse-orchestrator.desktop` |

Ensure `~/.local/bin` is on your **PATH** (default on many distributions).

### Uninstall

```bash
rm -rf ~/.local/share/SoundSpectrAnalyse
rm -f ~/.local/bin/soundspectranalyse-gui
rm -f ~/.local/share/applications/soundspectranalyse-orchestrator.desktop
```

### Audio and FFmpeg (optional)

```bash
# Ubuntu / Debian
sudo apt install -y ffmpeg

# Fedora
sudo dnf install -y ffmpeg
```

### Troubleshooting

| Issue | Action |
|-------|--------|
| `No module named '_tkinter'` | Install `python3-tk` (Debian/Ubuntu) or `python3-tkinter` (Fedora); run `./install-easy.sh` again. |
| Python &lt; 3.10 | Upgrade to Python 3.10 or 3.11 (`sudo apt install python3.11` or equivalent). |
| pip / compile error | Install build tools: `sudo apt install build-essential python3-dev`. |
| GUI over SSH only | Use a local graphical session or X11 forwarding; a display is required. |
| Network error | Check proxy and firewall; the script uses GitHub and PyPI. |

---

## Portable binary (PyInstaller) — developers

For developers with the project Python environment already configured.

```bash
cd ~/Desktop/instalers/linux
chmod +x *.sh
./build-all.sh
```

| Output (local `output/`, not in Git) | Description |
|--------------------------------------|-------------|
| `output/app/` | Folder with `SoundSpectrAnalyse-Orchestrator` |
| `output/SoundSpectrAnalyse-Linux-x86_64-3.7.0.tar.gz` | Archive for distribution |

From a portable build in `output/app/`:

```bash
./install-soundspectranalyse.sh
```

Creates the same `~/.local` shortcuts as the standard installer.
