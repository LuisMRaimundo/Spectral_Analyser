# Troubleshooting Orchestrator Startup

> **Legacy document — Tk orchestrator only.** The **canonical** batch pipeline is `python run_orchestrator.py` (or `soundspectranalyse` after `pip install -e .`). This page applies when you intentionally run **`pipeline_orchestrator_gui.py`** (legacy 90-tier Tk GUI / file picker), not the integrated preprocessing → analysis → compile workflow.

## Issue: Code Doesn't Start / Cursor Flashing

The **legacy Tk orchestrator** (`pipeline_orchestrator_gui.py`) is a **GUI application** that uses tkinter. When you run it, it should open a window.

## Diagnosis

✅ **All imports are working correctly** - tested and verified
✅ **No syntax errors** - code compiles successfully
✅ **All dependencies available** - numpy, pandas, librosa, etc.

## Possible Causes

### 1. GUI Window Not Visible
The window may have opened but is:
- **Minimized** - Check the taskbar
- **Behind other windows** - Press Alt+Tab to cycle through windows
- **On a different monitor** - If you have multiple displays

### 2. GUI Initialization Hang
The tkinter window might be stuck initializing. This can happen if:
- Display server issues
- tkinter backend problems
- Resource conflicts

### 3. Waiting for User Input
The GUI might be waiting for you to:
- Select a folder
- Click a button
- Interact with the interface

## Solutions

### Solution 1: Check if Window is Open
1. Press **Alt+Tab** to see all open windows
2. Look for a window titled **SoundSpectrAnalyse — Per-note Spectral Analysis** (Tk main window).
3. Check the **taskbar** for a Python/tkinter icon

### Solution 2: Check Task Manager
1. Open **Task Manager** (Ctrl+Shift+Esc)
2. Look for `python.exe` or `pythonw.exe` process
3. If it's running, the GUI is likely open but not visible

### Solution 3: Force Close and Restart
1. In Task Manager, end any `python.exe` processes
2. Try running again: `python pipeline_orchestrator_gui.py`
3. Watch for any error messages in the console

### Solution 4: Run with Verbose Output
```powershell
python pipeline_orchestrator_gui.py 2>&1 | Tee-Object -FilePath orchestrator_output.txt
```
This will save all output to a file so you can see what's happening.

### Solution 5: Test Tkinter
```powershell
python -c "import tkinter; print('tkinter OK')"
```
If this fails, reinstall Python with Tcl/Tk support or fix your display environment (Linux: `sudo apt install python3-tk` or use a desktop session).

## What Should Happen

When you run `python pipeline_orchestrator_gui.py`:
1. A tkinter window should open
2. You should see a GUI interface with buttons and options
3. The console should show log messages
4. The cursor should stop flashing once the GUI is ready

## If Window Still Doesn't Appear

1. **Check console output** - Look for error messages
2. **Try running from different directory** - Sometimes path issues cause problems
3. **Check Python/tkinter installation** - Run: `python -c "import tkinter; tkinter._test()"`
4. **Try running as administrator** - Sometimes permissions cause GUI issues

## Recent Changes

The code was recently updated to:
- Use bin-based percentages instead of peak-based (more accurate)
- Fix harmonic/inharmonic classification

These changes should **not** affect startup, but if issues persist, you can verify the changes are correct.

---

*Last updated: April 2026 — applies to package version 3.7.0 (`soundspectranalyse`).*
