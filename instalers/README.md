# SoundSpectrAnalyse — installers

**Repository:** https://github.com/LuisMRaimundo/SoundSpectrAnalyse

This folder contains scripts to install **SoundSpectrAnalyse** for users **without prior Python setup**. Open the folder for your operating system:

| Folder | System | Recommended entry point |
|--------|--------|-------------------------|
| **[`windows/`](windows/)** | Windows 10/11 (64-bit) | Double-click **`INSTALL.bat`** |
| **[`mac/`](mac/)** | macOS 11 or later | Run **`install-easy.sh`** |
| **[`linux/`](linux/)** | Linux (Ubuntu, Debian, Fedora, …) | Run **`install-easy.sh`** |

Each subfolder includes a **README with platform-specific installation instructions**.

## What the standard installer does

1. Installs or detects **Python 3.10 or 3.11** (on Windows, installs automatically if missing).
2. Fetches source from **https://github.com/LuisMRaimundo/SoundSpectrAnalyse** (`main` branch).
3. Creates an isolated environment and installs libraries from `requirements.txt`.
4. Adds a **shortcut** to launch the graphical interface (**SoundSpectrAnalyse Orchestrator**).

The first run may take **10–25 minutes** (download plus scientific packages). An **Internet connection** is required.

## Not included in Git

Folders `build/`, `dist/`, `output/`, and compiled `.exe` / `.zip` / `.dmg` artefacts are **not** committed. To distribute ready-made binaries, use [GitHub Releases](https://github.com/LuisMRaimundo/SoundSpectrAnalyse/releases).

## Portable builds (developers)

Each platform folder also provides **PyInstaller** scripts (`Build-All.ps1`, `build-all.sh`) to build standalone applications without Python on the target machine. These are intended for **developers** and are not recommended for end users.
