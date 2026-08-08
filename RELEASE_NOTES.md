# Release Notes

## V11.0

A large release focused on three things: a much wider action vocabulary, run controls that
actually work under pressure, and timing you can trust.

**Everything from V10.1 is still here.** No feature was removed. Saved profiles, recordings,
sequences and workspaces all load unchanged, and every V10.1 command-line flag still works.

### Downloads

| File | Size |
|---|---|
| `Builds/V11.0/Installer/AutoClickerInstaller.exe` | 76.9 MB |
| `Builds/V11.0/Executable/AutoClicker.exe` | 32.4 MB |
| `Builds/V11.0/Executable/AutoClickerLite.exe` | 31.9 MB |

The installer contains both applications. The executables are standalone and need no Python.

---

### Read this before upgrading

**Your click rate will roughly double at the same delay setting.**

PyAutoGUI adds a hidden 0.1 second pause to every call it makes. V10.1 never accounted for
it, so a delay of `0.10` produced about **5 actions per second** while the interface promised
10. V11.0 removes that hidden pause, so `0.10` now delivers the 10 per second it always
claimed.

If you have a profile tuned by feel, it will run about twice as fast as before. Two options:

- Double your delay value to keep the old speed, or
- Set **Pacing mode** to `Legacy V10.1` in *Timing and Repeat*, which reproduces the old
  behaviour exactly.

The readiness checklist now reports the real rate, and warns when Legacy pacing makes the
effective rate differ from the delay you typed.

**Enter no longer starts a run.** It used to be bound to the whole window, so pressing Enter
after typing a coordinate launched a live, uncapped run and immediately minimised the window.
Use **F5** to start, **F6** to pause, **Esc** to stop, or the buttons.

---

### New features

**A vocabulary beyond clicking.** The action list grew from 6 to 15 entries:

- `Key Press`, `Key Hold`, `Type Text` — keyboard automation
- `Scroll Up`, `Scroll Down` — wheel scrolling with a configurable notch count
- `Click And Hold`, `Drag To` — press-and-hold and click-drag
- `Move Only`, `Triple Left Click`

The **Action Setup** panel holds the parameters, and Quick Start tells you which ones the
selected action reads. Sequences accept the new actions too, so you can mix clicks, keys and
scrolls in one run.

**Pause and resume.** A Pause button sits between Start and Stop. It holds a run after the
current action without losing its position, and works for click runs, coordinate sequences
and recording playback alike.

**Hotkey Center.** Optional system-wide hotkeys for start, pause and capture-cursor, so the
app is drivable while minimised over the target window. Capture-by-hotkey also solves an old
annoyance: the *Use Current Cursor* button could only ever record the position of that
button. In-window shortcuts are F5 / F6 / Esc.

**Clicks-per-second targeting.** Type a target rate and the delay is derived for you, or read
the rate back from an existing delay. A live readout shows instant, average and peak rate
during a run.

**Scheduled start.** Give a `HH:MM` wall-clock time and the run arms itself until then. A
time earlier than now means tomorrow.

**Round-robin targets.** Cycle a recorded point list instead of hammering one coordinate.

**Run History.** Every finished run is appended to a rotating log in the app-data folder.
The viewer shows the log with lifetime totals that survive restarts, and exports to JSON.

**Profile undo.** Deleting a profile, or overwriting profiles on import, can now be undone.
If the disk write fails, the in-memory state rolls back rather than diverging.

**More themes and presets.** `Midnight` joins Light, Dark and Ocean, plus `System` which
follows your OS light/dark preference. A `Feather Touch` preset suits fragile or laggy UIs.

**A real command line.** `--help` and `--version` now work, along with 14 subcommands, a
stable JSON envelope and a documented exit-code contract:

```
python AutoClicker.py --help
python AutoClicker.py doctor          # health plus the exact pip command to fix it
python AutoClicker.py readiness NAME  # pre-flight a saved profile, no display needed
python AutoClicker.py history         # summarise the run log
python AutoClicker.py schema action   # what every action accepts
```

Exit codes: `0` success, `1` check or validation failure, `2` usage error, `3` internal error.

---

### Fixes

**Stop always works now.** The click run, sequence run and playback shared one stop signal,
and two of them cleared it on exit — so a finishing worker could restart a run you had
already stopped. Each subsystem now owns its own signal. The Stop button is also enabled
during sequences and playback, and the stop hotkey works in all three.

**A finished run can no longer orphan a live one.** Starting a run in the ~100 ms window
after a previous one ended left the new run with no handle: the Stop button went dead while
the mouse kept clicking. Run completion is now generation-guarded.

**Stop hotkeys that could never fire are rejected.** Entries like `a, b` or an unmapped key
name caused the underlying library to raise on every poll. The error was swallowed and the
readiness panel reported the hotkey as fine, leaving runs with no working stop key. These are
now caught before the run starts.

**Countdown no longer eats the runtime cap.** A 5-second countdown with a 3-second cap used
to produce a run that sent zero clicks. The cap now starts when the run does.

**Themes no longer corrupt.** Switching Dark to Light left the interface dark, and a further
switch produced white text on a light background — a state that persisted across restarts.
Verified across repeated switches through every theme.

**Crash safety.** The run loop, playback loop and interface update pump could each leak
global state or stop responding after a single error, requiring a restart. All three now
recover.

**The emergency hotkey saves your work.** `ctrl+shift+k` used to terminate the process
outright, discarding unsaved recordings and layout. It now stops everything, saves, and exits.

**Files are written atomically.** Saving a recording, sequence or profile export no longer
truncates the previous good file if the write is interrupted.

**Classic window (Old Style GUI).** *List Coordinates → Delete* always failed with an
internal error while the run list kept clicking the deleted point; the same path evaluated
listbox text as code. The stop hotkey silently killed only the worker thread, leaving the
interface showing an active run. Invalid coordinates fell through into the click loop.
The window itself also silently failed to open under some launch conditions.

**Photo Clicker** now tells you it needs OpenCV instead of leaking an internal message and
retrying forever, and reports a missing Pillow like Colour Clicker already did.
**Colour Clicker** no longer errors continuously if you close it mid-scan.

**Activity feed** kept 80 entries but only ever showed 12. It now has a scrollbar, copy and
export.

---

### Under the hood

- **~1,760 lines of dead code removed (22% of the file)**, including a 596-line window that
  was never reachable and four functions shadowed by later redefinitions.
- **Startup import dropped from ~15s to ~0.7s.** Four packages (`gspread`, `oauth2client`,
  `colormap`, `pywin32`) were installed and imported but never used by any code path. One of
  them pulled in matplotlib.
- **The main executable shrank 26%**, 45.6 MB to 32.4 MB, for the same reason.
- **136 automated tests**, up from 20, running on Windows and Linux across Python 3.10 and
  3.12. Previously the standard test command silently ran zero tests and reported success.
- Continuous integration added, including a scan that blocks credential files from being
  committed.
- Packaging now derives its version from a single source, verifies its inputs before
  deleting anything, bundles the window icon (previously missing from the frozen build), and
  refuses to delete a home directory or drive root via `--install-dir`.

### Dependencies

Only `pyautogui` and `keyboard` are required. Everything else is optional and the app
degrades gracefully without it. To see what you are missing:

```
python AutoClicker.py doctor
```

`opencv-python` is now listed — Photo Clicker's confidence matching has always needed it,
but it was never declared.

### Security

A Google service-account credential file that had been committed to this repository since
2020 has been removed from the working tree, and the ignore rules now block replacements.
**The key remains in the repository's git history and should be treated as compromised until
it is revoked.** No application code used it; the integration it belonged to was already dead.
