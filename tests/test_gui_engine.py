"""Behavioural tests for the run engine inside the Control Center class.

The engine lives inside `MAINWINDOW_REDESIGNED()`, so it can only be reached by building
the real window. These tests do that against a fake pyautogui that records calls instead
of moving the mouse, and skip cleanly on any machine without a display.
"""

import os
import tempfile
import time
import tkinter as tk
import types
import unittest

import AutoClicker


class FailSafeException(Exception):
    """Stand-in for pyautogui.FailSafeException."""


def make_fake_pyautogui(calls):
    return types.SimpleNamespace(
        FAILSAFE=True,
        PAUSE=0.1,
        size=lambda: (1920, 1080),
        position=lambda: (7, 9),
        click=lambda **kw: calls.append(("click", kw)),
        moveTo=lambda *a, **kw: calls.append(("moveTo", a, kw)),
        press=lambda keys: calls.append(("press", keys)),
        keyDown=lambda key: calls.append(("keyDown", key)),
        keyUp=lambda key: calls.append(("keyUp", key)),
        write=lambda message: calls.append(("write", message)),
        scroll=lambda clicks, **kw: calls.append(("scroll", clicks, kw)),
        mouseDown=lambda **kw: calls.append(("mouseDown", kw)),
        mouseUp=lambda **kw: calls.append(("mouseUp", kw)),
        FailSafeException=FailSafeException,
    )


def make_fake_keyboard():
    """Minimal stand-in for the `keyboard` package."""
    return types.SimpleNamespace(
        is_pressed=lambda key: False,
        add_hotkey=lambda *a, **k: object(),
        remove_hotkey=lambda handle: None,
        parse_hotkey=lambda hotkey: hotkey,
    )


def silence_dialogs():
    """Replace every blocking dialog with a no-op and return an undo callable.

    A modal `messagebox.showerror` has nobody to dismiss it on a CI runner: the job
    hangs until the platform's timeout. No test may be able to open one.
    """
    import tkinter.messagebox as messagebox

    names = ("showerror", "showinfo", "showwarning", "askyesno", "askyesnocancel", "askokcancel")
    saved = {name: getattr(messagebox, name, None) for name in names}
    replacements = {
        "showerror": lambda *a, **k: None,
        "showinfo": lambda *a, **k: None,
        "showwarning": lambda *a, **k: None,
        "askyesno": lambda *a, **k: True,
        "askyesnocancel": lambda *a, **k: True,
        "askokcancel": lambda *a, **k: True,
    }
    for name, replacement in replacements.items():
        setattr(messagebox, name, replacement)
        # AutoClicker did `from tkinter import messagebox`, so it shares this module object,
        # but rebind explicitly in case that ever changes.
        setattr(AutoClicker.messagebox, name, replacement)

    def restore():
        for name, original in saved.items():
            if original is not None:
                setattr(messagebox, name, original)
                setattr(AutoClicker.messagebox, name, original)

    return restore


_SHARED = {}


def get_shared_gui():
    """Build the Control Center exactly once for the whole test module.

    Tk does not survive repeated create/destroy cycles cleanly on Windows: a second
    root after a destroyed one raises `invalid command name "tcl_findLibrary"`. One
    window is built lazily, shared by every test, and left alive until the process ends.
    """
    if "gui" in _SHARED:
        return _SHARED["gui"]
    if _SHARED.get("unavailable"):
        raise unittest.SkipTest(_SHARED["unavailable"])

    calls = []
    _SHARED["calls"] = calls
    _SHARED["fake"] = make_fake_pyautogui(calls)
    _SHARED["real_pyautogui"] = AutoClicker.pyautogui
    _SHARED["real_keyboard"] = AutoClicker.keyboard
    AutoClicker.pyautogui = _SHARED["fake"]
    AutoClicker.keyboard = make_fake_keyboard()

    # We are supplying working stand-ins, so the dependency gate must not fire. Without
    # this, CI (which installs no third-party packages by design) reaches
    # _show_dependency_error and opens a modal dialog that never closes.
    _SHARED["import_errors"] = dict(AutoClicker.IMPORT_ERRORS)
    for package in ("pyautogui", "keyboard"):
        AutoClicker.IMPORT_ERRORS.pop(package, None)
    _SHARED["restore_dialogs"] = silence_dialogs()

    temp = tempfile.TemporaryDirectory()
    _SHARED["temp"] = temp
    _SHARED["env"] = {key: os.environ.get(key) for key in ("APPDATA", "LOCALAPPDATA")}
    os.environ["APPDATA"] = os.environ["LOCALAPPDATA"] = temp.name

    def give_up(reason):
        AutoClicker.pyautogui = _SHARED["real_pyautogui"]
        AutoClicker.keyboard = _SHARED["real_keyboard"]
        AutoClicker.IMPORT_ERRORS.clear()
        AutoClicker.IMPORT_ERRORS.update(_SHARED["import_errors"])
        _SHARED["restore_dialogs"]()
        _SHARED["unavailable"] = reason
        raise unittest.SkipTest(reason)

    holder = {}
    real_mainloop = tk.Tk.mainloop
    tk.Tk.mainloop = lambda window, *a, **k: holder.setdefault("gui", window)
    try:
        AutoClicker.MAINWINDOW_REDESIGNED()
    except Exception as exc:
        give_up(f"no usable display: {exc}")
    finally:
        tk.Tk.mainloop = real_mainloop

    if holder.get("gui") is None:
        give_up("Control Center did not build")

    _SHARED["gui"] = holder["gui"]
    return _SHARED["gui"]


class GuiTestCase(unittest.TestCase):
    """Base class sharing one Control Center; each test resets the state it relies on."""

    @classmethod
    def setUpClass(cls):
        cls.gui = get_shared_gui()
        cls.calls = _SHARED["calls"]
        cls.fake = _SHARED["fake"]

    def setUp(self):
        gui = self.gui
        gui.stopclick()
        self.pump(0.2)
        self.calls.clear()
        self.fake.PAUSE = 0.1
        self.fake.FAILSAFE = True
        gui.pause_event.clear()
        for event in (gui.stop_event, gui.sequence_stop_event, gui.playback_stop_event):
            event.clear()
        gui.recording_data = []
        gui.round_robin_var.set(False)
        gui.pacing_mode_var.set("Precise")
        gui.repeat_mode_var.set("Burst Count")
        gui.repeat_count_var.set("3")
        gui.stop_hotkey_var.set("esc")
        gui.countdown_var.set("0")
        gui.runtime_limit_var.set("0")
        gui.max_actions_var.set("0")
        gui.scheduled_start_var.set("")
        gui.click_mode_var.set("Left Click")
        gui.minimize_on_start_var.set(False)
        gui.play_sound_var.set(False)
        gui.dry_run_var.set(False)
        gui.human_like_var.set(False)
        gui.target_x_var.set("100")
        gui.target_y_var.set("200")
        gui.jitter_x_var.set("0")
        gui.jitter_y_var.set("0")
        gui.delay_var.set("0.01")
        self.addCleanup(self._stop_any_run)

    def _stop_any_run(self):
        try:
            self.gui.pause_event.clear()
            self.gui.stopclick()
            self.pump(0.4)
        except Exception:
            pass

    def pump(self, seconds):
        """Drive the Tk event loop for `seconds` so worker messages get delivered."""
        end = time.time() + seconds
        while time.time() < end:
            try:
                self.gui.update()
            except tk.TclError:
                return
            time.sleep(0.01)

    def clicks(self):
        return [call for call in self.calls if call[0] == "click"]


class RunEngineTests(GuiTestCase):
    # -- action dispatch ----------------------------------------------------------------

    def test_each_action_kind_reaches_the_right_call(self):
        expected = {
            "Left Click": "click", "Key Press": "press", "Key Hold": "keyDown",
            "Type Text": "write", "Scroll Up": "scroll", "Click And Hold": "mouseDown",
            "Drag To": "mouseDown", "Move Only": "moveTo",
        }
        self.gui.action_text_var.set("hi")
        for action, want in expected.items():
            with self.subTest(action=action):
                self.calls.clear()
                config = dict(self.gui._build_run_config(), click_mode=action,
                              dry_run=False, action_text="hi", stop_hotkey="")
                self.gui._emit_action(config, (100, 200))
                self.assertIn(want, [call[0] for call in self.calls])

    def test_held_actions_always_release(self):
        for action, down, up in (("Click And Hold", "mouseDown", "mouseUp"),
                                 ("Drag To", "mouseDown", "mouseUp"),
                                 ("Key Hold", "keyDown", "keyUp")):
            with self.subTest(action=action):
                self.calls.clear()
                config = dict(self.gui._build_run_config(), click_mode=action,
                              dry_run=False, hold_duration=0.01, stop_hotkey="")
                self.gui._emit_action(config, (10, 10))
                names = [call[0] for call in self.calls]
                self.assertIn(down, names)
                self.assertIn(up, names)

    def test_dry_run_emits_nothing(self):
        config = dict(self.gui._build_run_config(), dry_run=True, stop_hotkey="")
        self.gui._emit_action(config, (100, 200))
        self.assertEqual(self.calls, [])

    # -- run lifecycle ------------------------------------------------------------------

    def test_burst_sends_exactly_the_requested_count(self):
        self.gui.repeat_mode_var.set("Burst Count")
        self.gui.repeat_count_var.set("5")
        self.gui.startclick()
        self.pump(2.0)
        self.assertEqual(len(self.clicks()), 5)

    def test_globals_are_restored_after_a_run(self):
        self.gui.repeat_mode_var.set("Burst Count")
        self.gui.repeat_count_var.set("3")
        self.gui.startclick()
        self.pump(2.0)
        self.assertEqual(self.fake.PAUSE, 0.1)
        self.assertTrue(self.fake.FAILSAFE)

    def test_precise_pacing_zeroes_the_library_pause_during_the_run(self):
        seen = []
        real_click = self.fake.click
        self.fake.click = lambda **kw: (seen.append(self.fake.PAUSE), real_click(**kw))
        self.gui.repeat_mode_var.set("Burst Count")
        self.gui.repeat_count_var.set("3")
        self.gui.pacing_mode_var.set("Precise")
        self.gui.startclick()
        self.pump(2.0)
        self.assertTrue(seen)
        self.assertTrue(all(pause == 0 for pause in seen), seen)

    def test_legacy_pacing_leaves_the_library_pause_alone(self):
        seen = []
        real_click = self.fake.click
        self.fake.click = lambda **kw: (seen.append(self.fake.PAUSE), real_click(**kw))
        self.gui.repeat_mode_var.set("Burst Count")
        self.gui.repeat_count_var.set("3")
        self.gui.pacing_mode_var.set("Legacy V10.1")
        self.gui.startclick()
        self.pump(2.0)
        self.assertTrue(seen)
        self.assertTrue(all(pause == 0.1 for pause in seen), seen)

    def test_pause_holds_the_run_and_resume_continues_it(self):
        self.gui.repeat_mode_var.set("Infinite")
        self.gui.stop_hotkey_var.set("f24")
        self.gui.delay_var.set("0.02")
        self.gui.startclick()
        self.pump(0.4)
        self.gui.toggle_pause()
        self.pump(0.3)
        at_pause = len(self.clicks())
        self.pump(0.5)
        after_wait = len(self.clicks())
        self.assertLessEqual(after_wait - at_pause, 1, "run kept clicking while paused")
        self.assertEqual(self.gui.pause_button.cget("text"), "Resume")

        self.gui.toggle_pause()
        self.pump(0.4)
        self.assertGreater(len(self.clicks()), after_wait, "run did not resume")

    def test_stop_ends_the_run_and_restores_the_buttons(self):
        self.gui.repeat_mode_var.set("Infinite")
        self.gui.stop_hotkey_var.set("f24")
        self.gui.startclick()
        self.pump(0.3)
        self.gui.stopclick()
        self.pump(0.6)
        self.assertFalse(self.gui.worker_thread and self.gui.worker_thread.is_alive())
        self.assertEqual(str(self.gui.start_button.cget("state")), "normal")
        self.assertEqual(str(self.gui.stop_button.cget("state")), "disabled")

    def test_a_stale_finish_cannot_tear_down_a_newer_run(self):
        # The pump runs every 100ms; a run started inside that window used to be orphaned
        # by the previous run's "finished" message, leaving Stop dead while clicks flowed.
        self.gui.repeat_mode_var.set("Burst Count")
        self.gui.repeat_count_var.set("200")
        self.gui.delay_var.set("0.05")
        self.gui.startclick()
        self.pump(0.2)
        self.gui._finish_run(1, 0.1, (0, 0), generation=self.gui.active_run_generation - 1)
        self.assertTrue(self.gui.worker_thread and self.gui.worker_thread.is_alive())
        self.assertEqual(str(self.gui.stop_button.cget("state")), "normal")

    def test_countdown_is_not_charged_against_the_runtime_cap(self):
        # A 0.5s countdown with a 0.4s cap used to break on the first iteration: 0 actions.
        self.gui.repeat_mode_var.set("Infinite")
        self.gui.stop_hotkey_var.set("f24")
        self.gui.countdown_var.set("0.5")
        self.gui.runtime_limit_var.set("0.4")
        self.gui.startclick()
        self.pump(1.8)
        self.assertGreater(len(self.clicks()), 0)

    def test_an_unpollable_stop_hotkey_is_rejected_before_the_run(self):
        self.gui.stop_hotkey_var.set("a, b")
        with self.assertRaises(ValueError):
            self.gui._build_run_config()

    def test_round_robin_cycles_every_recorded_point(self):
        self.gui.recording_data = [(10, 10), (20, 20), (30, 30)]
        self.gui.round_robin_var.set(True)
        self.gui.repeat_mode_var.set("Burst Count")
        self.gui.repeat_count_var.set("6")
        self.gui.startclick()
        self.pump(2.0)
        points = {(call[1]["x"], call[1]["y"]) for call in self.clicks()}
        self.assertEqual(points, {(10, 10), (20, 20), (30, 30)})

    def test_stop_tokens_are_independent_per_subsystem(self):
        # One shared Event let a finishing worker un-stop a running one.
        self.gui.stop_event.set()
        self.gui.playback_stop_event.set()
        self.gui.playback_stop_event.clear()
        self.assertTrue(self.gui.stop_event.is_set())
        self.gui.stop_event.clear()

    def test_finished_runs_are_written_to_the_persistent_log(self):
        self.gui.repeat_mode_var.set("Burst Count")
        self.gui.repeat_count_var.set("4")
        self.gui.startclick()
        self.pump(2.0)
        records = AutoClicker._read_run_log(
            AutoClicker._state_file_location(AutoClicker.RUN_LOG_FILE_NAME)
        )
        self.assertTrue(records)
        self.assertGreater(AutoClicker._summarize_run_history(records)["actions"], 0)


class ThemeTests(GuiTestCase):
    def tearDown(self):
        self.gui.theme_var.set("Light")
        self.gui._apply_theme()

    def test_repeated_theme_switches_never_corrupt_the_palette(self):
        # Themes used to be re-derived from live colours, and Light hero_bg equals Dark
        # main_bg, so Dark -> Light left the page dark and the next switch made text
        # unreadable. Roles are now captured once from the authored colour.
        expected = {"Light": "#dbe7f2", "Dark": "#0f172a", "Ocean": "#d8edf2", "Midnight": "#08070f"}
        for name in ("Light", "Dark", "Ocean", "Midnight", "Light", "Dark", "Light", "Ocean", "Light"):
            with self.subTest(theme=name):
                self.gui.theme_var.set(name)
                self.gui._apply_theme()
                self.gui.update()
                self.assertEqual(self.gui.cget("bg"), expected[name])

    def test_system_theme_resolves_to_a_real_palette(self):
        self.gui.theme_var.set("System")
        palette = self.gui._theme_palette()
        self.assertIn(palette["main_bg"], ("#dbe7f2", "#0f172a"))


if __name__ == "__main__":
    unittest.main()
