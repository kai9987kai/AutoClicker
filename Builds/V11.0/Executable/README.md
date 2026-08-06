# AutoClicker

Windows desktop input-automation utilities built in Python with Tkinter and PyAutoGUI.

## Current apps

- `AutoClicker.py`
  The full Control Center experience with profiles, quick tools, recording/playback, tray support, and richer run controls.
- `lite-version.py`
  A smaller launcher for fast coordinate clicking with burst mode and safer stop handling.

## What is new in V11.0

V11.0 is additive: every V10.1 feature is still present. The headline changes are a wider
action vocabulary, real pause/resume, honest timing, and a proper command line.

### New capabilities

- **Beyond clicking.** The action list now covers `Key Press`, `Key Hold`, `Type Text`,
  `Scroll Up`/`Scroll Down`, `Click And Hold`, `Drag To`, `Move Only` and `Triple Left Click`
  alongside all six original click types. Sequences accept the new actions too.
- **Pause and resume.** A Pause button sits beside Start/Stop and holds a run after the
  current action without losing its position. Works for click runs, sequences and playback.
- **Hotkey Center.** Optional system-wide hotkeys for start, pause and capture-cursor, so the
  app is drivable while minimised over the target window. In-window: `F5` start, `F6` pause,
  `Esc` stop.
- **Clicks-per-second targeting.** Enter a target rate and the app derives the delay, or read
  the rate back from an existing delay. Live instant/average/peak rate shows during a run.
- **Scheduled start.** Give a `HH:MM` wall-clock time and the run arms itself until then.
- **Round-robin targets.** Cycle a recorded point list instead of hammering one coordinate.
- **Run history.** Every finished run is appended to a rotating log under the app-data folder,
  with a viewer (`Run History`), lifetime totals that survive restarts, and JSON export.
- **New themes.** `Midnight`, plus `System` which follows the OS light/dark preference.
- **`Feather Touch` behaviour preset** for fragile or laggy UIs.
- **Real CLI.** `--help`, `--version`, subcommands, a stable JSON envelope, and a documented
  exit-code contract (see below).

### Fixes worth knowing about

- **Timing is now honest.** PyAutoGUI adds a hidden 0.1s pause to every call, so a `0.10`
  delay actually produced about 5 actions/sec while the UI promised 10. `Precise` pacing
  (the new default) zeroes that pause; `Legacy V10.1` pacing restores the old behaviour
  exactly if you were relying on it. The readiness panel reports the real rate.
- **Stop always works.** The click run, sequence run and playback each own their stop
  signal. Previously one finishing worker cleared the shared flag and could restart a run
  the user had already stopped. The Stop button is now enabled during sequences and playback,
  and the stop hotkey works in all three.
- **Inert stop hotkeys are caught.** A hotkey `keyboard` cannot poll (for example `a, b`, or
  an unmapped key name) is now rejected at validation time instead of being reported green
  and silently never firing.
- **Countdown no longer eats the runtime cap.** A 5s countdown with a 3s cap used to produce
  a zero-action run. The cap now starts when the run does.
- **Themes no longer corrupt.** Switching Dark to Light left the UI dark, and a further
  switch produced white text on a light page. Widgets now remember their palette role.
- **Crash-safety.** The run loop, playback loop and UI pump all restore global state and keep
  running after an error, instead of wedging the app until restart.
- **The emergency hotkey saves your work.** `ctrl+shift+k` stops everything, persists the
  workspace, then exits, instead of calling `os._exit(0)` and discarding unsaved state.
- **Files are written atomically.** Saving a recording, sequence or profile export no longer
  truncates the previous good file if the write is interrupted.
- **22% smaller, 10x faster to import.** ~1,760 lines of dead and shadowed code removed, and
  four unused packages (`gspread`, `oauth2client`, `colormap`, `pywin32`) dropped. `import
  AutoClicker` went from ~15s to ~1.4s.

## Existing highlights (all retained)

- V10.1 Safety Guard with optional PyAutoGUI corner fail-safe control, max action caps, run validation, and live run intelligence.
- V10.1 command-strip safety controls with dry-run, fail-safe, validation, health, session report, and state-folder shortcuts.
- V10.1 Support Hub in the right rail for health checks, session reports, state backups, and opening the app-data folder.
- V10.1 run readiness checklist in Live Review with target, output, fail-safe, stop-boundary, pace, and stop-hotkey checks.
- V10.1 Safety Guard presets for Simulation, Guarded Live, and Manual Stop Live modes.
- V10.1 profile state in Live Review shows saved, modified, new, or missing profile state for the current controls.
- V10.1 support bundle workflow packages health, session, state summary, and known app-state backup files for troubleshooting.
- V10.1 dry-run mode for simulating click runs, sequence runs, and recording playback without sending mouse clicks.
- V10.1 session report export with recent activity, run summaries, active profile settings, and state-file paths.
- V10.1 profile/workspace persistence in the user app-data directory with migration from legacy local files.
- V10.1 profile import preview, profile JSON validator, and state backup manifests.
- V10 scroll-first tool windows for Photo Clicker, Colour Clicker, Recording Studio, and Sequence Builder.
- Photo presets, click offsets, settle delay, cursor-focused region tools, and match chime support in Photo Clicker.
- Colour presets, recent swatches, max-click caps, cursor-focused scan regions, and safer pipette hotkey cleanup in Colour Clicker.
- Recording Studio supports duplicate, move, reverse, offset, and direct handoff into the sequence workflow.
- Sequence Builder supports selected-step editing, reverse order, loop counts, countdowns, and running from the selected step.
- V9 accordion-style control center with dropdown sections so the main page starts compact.
- Quick action strip for start, stop, capture, preset application, and section reveal/hide control.
- Innovation Lab presets including `Balanced`, `Precision`, `Burst Sprint`, and `Human Mimic`.
- Optional micro-pause rhythm controls for long sessions.
- Scrollable control center with vertical and horizontal scrollbars.
- Window Studio controls for theme switching, opacity, UI scale, size presets, fullscreen, and tray-close behaviour.
- Saved profile import/export from JSON, workspace persistence, runtime caps, and delay variance.
- Health Check window, session activity feed, tray restore, and graceful dependency handling.

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

- current-cursor capture (via a global hotkey, so it no longer captures its own button)
- infinite or burst runs
- configurable stop hotkey
- left, right, middle, and double-left click modes

## Main app workflow

1. Capture or enter a target X/Y coordinate.
2. Choose an action type, delay (or target actions/sec), optional delay variance, jitter, and countdown.
3. Fill in any action parameters the chosen action needs — the Quick Start panel tells you which.
4. Pick either `Infinite` or `Burst Count`.
5. Set a stop hotkey for any infinite run.
6. Press `Start` (or `F5`).

Optional tools inside the full app:

- Coordinate finder, coordinate sequence builder, Recording Studio
- Health Check, Run History, Safety Guard and plan validation
- Run readiness checklist, safety presets, profile state review
- Support bundle creation, dry-run simulation, session report export
- Photo clicker, colour clicker, recording and playback, saved profiles

## Generated local files

Stored under the user app-data directory, usually `%APPDATA%\AutoClicker`:

- `autoclicker_profiles.json` — saved clicker profiles.
- `autoclicker_workspace.json` — restored workspace state.
- `autoclicker_runs.log` — one JSON line per finished run, rotated at 1 MB to `.log.1`.

If older copies exist beside the script, the app copies them forward on first launch. The
legacy local filenames remain ignored by git.

## Command line

```bash
python AutoClicker.py --help
python AutoClicker.py --version
```

| Command | What it does |
|---|---|
| `health [--strict] [--json]` | dependency, version and state-file report; `--strict` exits 1 on a missing required package |
| `doctor` | health plus the exact `pip install` line that fixes it |
| `state-summary [--json]` | summarise the saved profile and workspace files |
| `backup-state [DIR] [--dry-run] [--json]` | copy app-state files into a timestamped folder |
| `support-bundle [DIR] [--json]` | write a full troubleshooting bundle (previously GUI-only) |
| `validate-recording PATH...` | validate one or more recording files |
| `validate-sequence PATH...` | validate one or more sequence files |
| `validate-profiles PATH...` | validate one or more profile files |
| `profile-preview PATH... [--show-values]` | preview importing profiles over the saved set |
| `profiles [NAME] [--json]` | list saved profiles, or show one |
| `readiness NAME [--json]` | run the pre-flight checklist against a saved profile, no display needed |
| `schema {recording,sequence,profile,action}` | print the accepted file/action shapes |
| `history [--limit N] [--json]` | summarise the persistent run log |
| `gui` | open the Control Center (also the default with no arguments) |

Every command accepts `--json`, which emits a stable envelope:
`{schema_version, app_version, command, ok, generated_at, data, errors}`.

**Exit codes:** `0` success, `1` check or validation failure, `2` usage error, `3` internal error.

All V10.1 flags (`--health-check`, `--health-json`, `--state-summary`, `--state-json`,
`--backup-state`, `--validate-recording`, `--validate-sequence`, `--validate-profiles`,
`--profile-import-preview`) still work and are translated to the new subcommands. Two
differences, both deliberate: an unrecognised flag is now a usage error instead of silently
opening the GUI, and stacking two legacy commands reports the extra one instead of dropping
it behind a success exit code.

## Dependencies

Required — the app cannot send input without these:

- `pyautogui`
- `keyboard`

Optional — each unlocks a feature and degrades gracefully when absent:

- `pystray` — close-to-tray and the tray menu
- `Pillow` — Photo Clicker previews and screen sampling
- `numpy` — fast Colour Clicker region scanning
- `opencv-python` — Photo Clicker confidence matching
- `win10toast` — Windows toast notifications

## Dependency troubleshooting

Ask the app what is missing:

```bash
python AutoClicker.py doctor
```

It prints the exact install command for anything absent. Or reinstall everything:

```bash
pip install -r requirements.txt
```

## Running the tests

```bash
python -m unittest discover -s tests -t . -v
```

`pytest` also works from the repository root. CI runs the suite on Windows and Linux across
Python 3.10 and 3.12; the tests need no third-party package.

## Building a release

```bash
pip install -r requirements-build.txt
python packaging/build_release.py
```

The build reads its version straight from `APP_VERSION` in `AutoClicker.py`, checks its
inputs before deleting anything, and verifies the artifacts it produced.
