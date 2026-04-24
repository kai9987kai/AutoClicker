# AutoClicker

Windows desktop auto-clicker utilities built in Python with Tkinter and PyAutoGUI.

## Current apps

- `AutoClicker.py`
  The full Control Center experience with profiles, quick tools, recording/playback, tray support, and richer run controls.
- `lite-version.py`
  A smaller launcher for fast coordinate clicking with burst mode and safer stop handling.

## Newer full-app highlights

- V9 accordion-style control center with dropdown sections so the main page starts compact instead of showing every option at once.
- Quick action strip for start, stop, capture, preset application, and section reveal/hide control.
- Innovation Lab presets including `Balanced`, `Precision`, `Burst Sprint`, and `Human Mimic`.
- Optional micro-pause rhythm controls for long sessions to break up repetitive runs.
- Scrollable control center with vertical and horizontal scrollbars for smaller screens and denser setups.
- New Window Studio controls for theme switching, opacity, UI scale, size presets, fullscreen, and tray-close behaviour.
- Improved theme handling with Light, Dark, and Ocean modes across the main control center.
- Redesigned control center layout with clearer planner, tools, summary, and activity sections.
- Saved profile import/export from JSON.
- Workspace persistence for the last-used setup, recording points, and recent activity.
- Runtime cap support for auto-stopping long runs.
- Delay variance support for less rigid timing.
- Stronger sequence builder with validation, reordering, duplication, and recording import.
- Recording Studio for saving, loading, trimming, and reusing captured points.
- Health Check window for dependency visibility, session state, and local config files.
- Session activity feed for starts, stops, profile actions, and playback.
- Improved tray restore, dependency handling, and shutdown cleanup.

## Full app quick start

1. Install Python 3.10+ on Windows.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Launch the main app:

```bash
python AutoClicker.py
```

## Lite app quick start

```bash
python lite-version.py
```

The lite app supports:

- current-cursor capture
- infinite or burst runs
- configurable stop hotkey
- left, right, middle, and double-left click modes

## Main app workflow

1. Capture or enter a target X/Y coordinate.
2. Choose click type, delay, optional delay variance, jitter, and countdown.
3. Pick either `Infinite` or `Burst Count`.
4. Set a stop hotkey for any infinite run.
5. Press `Start`.

Optional tools inside the full app:

- Coordinate finder
- Coordinate sequence builder
- Recording Studio
- Health Check
- Photo clicker
- Colour clicker
- Recording and playback
- Saved profiles

## Generated local files

- `autoclicker_profiles.json`
  Saved clicker profiles from the full app.
- `autoclicker_workspace.json`
  Restored workspace state for the full app.

These files are ignored by git.

## Dependencies

- `pyautogui`
- `keyboard`
- `pystray`
- `Pillow`
- `pywin32`
- `numpy`

Some legacy optional features also use:

- `gspread`
- `oauth2client`
- `win10toast`
- `colormap`

## Dependency troubleshooting

The project now fails more gracefully when a package is missing, but the core clickers still need:

- `pyautogui`
- `keyboard`

If the full app or lite app reports a missing dependency, install the requirements again:

```bash
pip install -r requirements.txt
```
