# AutoClicker

Windows desktop auto-clicker utilities built in Python with Tkinter and PyAutoGUI.

## Current apps

- `AutoClicker.py`
  The full Control Center experience with profiles, quick tools, recording/playback, tray support, and richer run controls.
- `lite-version.py`
  A smaller launcher for fast coordinate clicking with burst mode and safer stop handling.

## Newer full-app highlights

- V10.1 Safety Guard with optional PyAutoGUI corner fail-safe control, max action caps, run validation, and live run intelligence.
- V10.1 dry-run mode for simulating click runs, sequence runs, and recording playback without sending mouse clicks.
- V10.1 session report export with recent activity, run summaries, active profile settings, and state-file paths.
- V10.1 profile/workspace persistence moved to the user app-data directory with migration from legacy local files.
- V10.1 headless state summary, state backup, recording validator, and sequence validator commands.
- V10.1 profile import preview and profile JSON validator.
- V10.1 state backup manifests for support-friendly backup folders.
- V10.1 headless health check via `python AutoClicker.py --health-check` or `python AutoClicker.py --health-json` for support and packaging verification.
- V10.1 release packaging no longer bundles `creds.json`.
- V10 scroll-first tool windows for Photo Clicker, Colour Clicker, Recording Studio, and Sequence Builder so every control stays reachable on smaller screens.
- New photo presets, click offsets, settle delay, cursor-focused region tools, and match chime support in Photo Clicker.
- New colour presets, recent swatches, max-click caps, cursor-focused scan regions, and safer pipette hotkey cleanup in Colour Clicker.
- Recording Studio now supports duplicate, move, reverse, offset, and direct handoff into the sequence workflow.
- Sequence Builder now supports selected-step editing, reverse order, loop counts, countdowns, and running from the selected step.
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
- Safety Guard and plan validation
- Dry-run simulation
- Session report export
- Photo clicker
- Colour clicker
- Recording and playback
- Saved profiles

## Generated local files

- `autoclicker_profiles.json`
  Saved clicker profiles from the full app.
- `autoclicker_workspace.json`
  Restored workspace state for the full app.

New V10.1 runs store these files under the user app-data directory, usually `%APPDATA%\AutoClicker`.
If older copies exist beside the script, the app copies them forward on first launch. The legacy local filenames remain ignored by git.

## Headless support commands

```bash
python AutoClicker.py --health-check
python AutoClicker.py --health-json
python AutoClicker.py --state-summary
python AutoClicker.py --state-json
python AutoClicker.py --backup-state
python AutoClicker.py --validate-profiles path/to/profiles.json
python AutoClicker.py --profile-import-preview path/to/profiles.json
python AutoClicker.py --validate-recording path/to/recording.json
python AutoClicker.py --validate-sequence path/to/sequence.json
```

These print dependency, version, resource, state-file, backup, and validator information without opening the Tkinter UI. JSON forms are meant for scripts and support bundles.

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
