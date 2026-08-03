"""Tests for the V11 run-engine primitives.

Everything here is headless: no display, no real mouse, no pyautogui calls.
"""

import datetime
import unittest

import AutoClicker


class InterruptibleSleepTests(unittest.TestCase):
    def _fake_clock(self, sleeps):
        state = {"now": 0.0}

        def clock():
            return state["now"]

        def sleeper(duration):
            sleeps.append(duration)
            state["now"] += duration

        return clock, sleeper

    def test_sleeps_the_full_duration_in_slices(self):
        sleeps = []
        clock, sleeper = self._fake_clock(sleeps)
        completed = AutoClicker._interruptible_sleep(0.1, None, 0.02, clock, sleeper)

        self.assertTrue(completed)
        self.assertAlmostEqual(sum(sleeps), 0.1, places=6)
        self.assertLessEqual(max(sleeps), 0.02)

    def test_returns_early_when_the_gate_trips(self):
        sleeps = []
        clock, sleeper = self._fake_clock(sleeps)
        calls = {"n": 0}

        def should_stop():
            calls["n"] += 1
            return calls["n"] > 2

        completed = AutoClicker._interruptible_sleep(10.0, should_stop, 0.02, clock, sleeper)

        self.assertFalse(completed)
        self.assertLess(sum(sleeps), 0.1)

    def test_never_passes_a_negative_duration_to_sleep(self):
        # The old loop re-read the clock between the guard and the argument, so a
        # descheduled thread could compute a negative sleep and raise ValueError.
        sleeps = []
        state = {"now": 0.0}

        def clock():
            state["now"] += 0.05  # Clock jumps past the deadline mid-iteration.
            return state["now"]

        def sleeper(duration):
            sleeps.append(duration)

        AutoClicker._interruptible_sleep(0.01, None, 0.02, clock, sleeper)
        self.assertTrue(all(duration >= 0 for duration in sleeps), sleeps)

    def test_zero_and_invalid_durations_do_not_sleep(self):
        sleeps = []
        clock, sleeper = self._fake_clock(sleeps)
        self.assertTrue(AutoClicker._interruptible_sleep(0, None, 0.02, clock, sleeper))
        self.assertTrue(AutoClicker._interruptible_sleep("nonsense", None, 0.02, clock, sleeper))
        self.assertEqual(sleeps, [])

    def test_zero_duration_still_reports_a_tripped_gate(self):
        self.assertFalse(AutoClicker._interruptible_sleep(0, lambda: True))


class ResolveActionTests(unittest.TestCase):
    def test_every_registry_entry_resolves(self):
        # action_text has no usable default on purpose: typing needs real text.
        config = {"x": 10, "y": 20, "action_text": "hello"}
        for action_name in AutoClicker.ACTION_REGISTRY:
            with self.subTest(action=action_name):
                descriptor = AutoClicker._resolve_action(action_name, config)
                self.assertIn("kind", descriptor)
                self.assertIn("call", descriptor)
                self.assertIsInstance(descriptor["kwargs"], dict)

    def test_defaults_cover_every_declared_parameter(self):
        declared = {name for spec in AutoClicker.ACTION_REGISTRY.values() for name in spec.get("uses", ())}
        self.assertEqual(declared - set(AutoClicker.ACTION_DEFAULTS), set())

    def test_legacy_click_types_keep_their_exact_behaviour(self):
        for label, (button, clicks) in AutoClicker.DEFAULT_CLICK_TYPES.items():
            with self.subTest(label=label):
                descriptor = AutoClicker._resolve_action(label, {"x": 3, "y": 4})
                self.assertEqual(descriptor["kind"], "click")
                self.assertEqual(descriptor["kwargs"]["button"], button)
                self.assertEqual(descriptor["kwargs"]["clicks"], clicks)
                self.assertEqual((descriptor["kwargs"]["x"], descriptor["kwargs"]["y"]), (3, 4))

    def test_scroll_direction_is_signed(self):
        up = AutoClicker._resolve_action("Scroll Up", {"scroll_amount": 5})
        down = AutoClicker._resolve_action("Scroll Down", {"scroll_amount": 5})
        self.assertEqual(up["kwargs"]["clicks"], 5)
        self.assertEqual(down["kwargs"]["clicks"], -5)

    def test_scroll_amount_sign_is_normalised(self):
        descriptor = AutoClicker._resolve_action("Scroll Up", {"scroll_amount": -7})
        self.assertEqual(descriptor["kwargs"]["clicks"], 7)

    def test_drag_carries_both_endpoints(self):
        descriptor = AutoClicker._resolve_action(
            "Drag To", {"x": 1, "y": 2, "drag_to_x": 30, "drag_to_y": 40}
        )
        self.assertEqual(descriptor["kwargs"]["x"], 1)
        self.assertEqual(descriptor["kwargs"]["to_y"], 40)

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            AutoClicker._resolve_action("Telepathy", {})

    def test_empty_key_name_is_rejected(self):
        with self.assertRaises(ValueError):
            AutoClicker._resolve_action("Key Press", {"action_key": "   "})

    def test_zero_scroll_is_rejected(self):
        with self.assertRaises(ValueError):
            AutoClicker._resolve_action("Scroll Up", {"scroll_amount": 0})

    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):
            AutoClicker._resolve_action("Type Text", {"action_text": ""})

    def test_keyboard_actions_do_not_move_the_pointer(self):
        self.assertFalse(AutoClicker._action_moves_pointer("Key Press"))
        self.assertFalse(AutoClicker._action_moves_pointer("Type Text"))
        self.assertTrue(AutoClicker._action_moves_pointer("Left Click"))
        self.assertTrue(AutoClicker._action_moves_pointer("Scroll Up"))


class RateTests(unittest.TestCase):
    def test_delay_and_cps_round_trip(self):
        self.assertAlmostEqual(AutoClicker._cps_to_delay(10), 0.1)
        self.assertAlmostEqual(AutoClicker._delay_to_cps(0.1), 10.0)
        self.assertAlmostEqual(AutoClicker._delay_to_cps(AutoClicker._cps_to_delay(7)), 7.0)

    def test_non_positive_and_invalid_values_return_none(self):
        for value in (0, -1, "", "abc", None):
            self.assertIsNone(AutoClicker._cps_to_delay(value))
            self.assertIsNone(AutoClicker._delay_to_cps(value))

    def test_rate_stats_reports_average_and_peak(self):
        stats = AutoClicker._rate_stats([(0.0, 0), (1.0, 10), (2.0, 30)])
        self.assertEqual(stats["average_cps"], 15.0)
        self.assertEqual(stats["peak_cps"], 20.0)
        self.assertEqual(stats["samples"], 3)

    def test_rate_stats_handles_too_few_samples(self):
        for samples in ([], [(0.0, 0)], None):
            stats = AutoClicker._rate_stats(samples)
            self.assertEqual(stats["average_cps"], 0.0)
            self.assertEqual(stats["peak_cps"], 0.0)

    def test_instant_rate_follows_the_recent_window(self):
        # Fast for 10s, then a slow final second: instant should track the slow tail.
        samples = [(float(second), second * 20) for second in range(11)]
        samples.append((11.0, 201))
        stats = AutoClicker._rate_stats(samples, window_seconds=1.0)
        self.assertLess(stats["instant_cps"], stats["average_cps"])


class PacingTests(unittest.TestCase):
    def test_precise_mode_honours_the_configured_delay(self):
        self.assertAlmostEqual(AutoClicker._effective_action_period(0.1, "Precise", False), 0.1)

    def test_legacy_mode_exposes_the_hidden_library_pause(self):
        # V10.1 promised 10/sec at delay 0.10 while actually delivering about 5/sec.
        legacy = AutoClicker._effective_action_period(0.1, "Legacy V10.1", False)
        self.assertAlmostEqual(legacy, 0.2)
        self.assertAlmostEqual(AutoClicker._delay_to_cps(legacy), 5.0)

    def test_human_like_adds_movement_overhead(self):
        plain = AutoClicker._effective_action_period(0.1, "Precise", False)
        humanised = AutoClicker._effective_action_period(0.1, "Precise", True)
        self.assertGreater(humanised, plain)

    def test_invalid_and_negative_delays_are_clamped(self):
        self.assertAlmostEqual(AutoClicker._effective_action_period(-5, "Precise", False), 0.0)
        self.assertAlmostEqual(AutoClicker._effective_action_period("x", "Precise", False), 0.0)


class HotkeyValidationTests(unittest.TestCase):
    def test_multi_step_hotkeys_are_rejected(self):
        result = AutoClicker._validate_hotkey("a, b")
        self.assertFalse(result["valid"])
        self.assertIn("Multi-step", result["reason"])

    def test_blank_hotkey_is_reported_as_unset(self):
        self.assertFalse(AutoClicker._validate_hotkey("")["valid"])
        self.assertFalse(AutoClicker._validate_hotkey(None)["valid"])

    def test_parser_failure_is_surfaced_not_swallowed(self):
        def exploding_parser(_value):
            raise ValueError("no such key")

        result = AutoClicker._validate_hotkey("f13", parser=exploding_parser)
        self.assertFalse(result["valid"])
        self.assertIn("no such key", result["reason"])

    def test_a_parseable_hotkey_is_accepted(self):
        result = AutoClicker._validate_hotkey("ctrl+k", parser=lambda value: value)
        self.assertTrue(result["valid"])
        self.assertEqual(result["hotkey"], "ctrl+k")


class ScheduledStartTests(unittest.TestCase):
    def test_blank_value_is_not_scheduled(self):
        self.assertFalse(AutoClicker._parse_scheduled_start("")["scheduled"])

    def test_a_later_time_today_waits_that_long(self):
        now = datetime.datetime(2026, 8, 3, 9, 0, 0)
        result = AutoClicker._parse_scheduled_start("09:30", now=now)
        self.assertTrue(result["scheduled"])
        self.assertAlmostEqual(result["delay_seconds"], 1800.0)

    def test_an_earlier_time_rolls_over_to_tomorrow(self):
        now = datetime.datetime(2026, 8, 3, 20, 0, 0)
        result = AutoClicker._parse_scheduled_start("09:00", now=now)
        self.assertAlmostEqual(result["delay_seconds"], 13 * 3600.0)
        self.assertTrue(result["start_at"].startswith("2026-08-04"))

    def test_seconds_precision_is_accepted(self):
        now = datetime.datetime(2026, 8, 3, 9, 0, 0)
        result = AutoClicker._parse_scheduled_start("09:00:30", now=now)
        self.assertAlmostEqual(result["delay_seconds"], 30.0)

    def test_malformed_time_reports_an_error(self):
        result = AutoClicker._parse_scheduled_start("half past nine")
        self.assertIn("error", result)
        self.assertFalse(result["scheduled"])


class GeometryClampTests(unittest.TestCase):
    def test_offscreen_geometry_is_pulled_back(self):
        clamped = AutoClicker._clamp_geometry_to_screen("800x600+5000+4000", 1920, 1080)
        self.assertEqual(clamped, "800x600+1840+1000")

    def test_onscreen_geometry_is_untouched(self):
        self.assertEqual(
            AutoClicker._clamp_geometry_to_screen("800x600+100+100", 1920, 1080),
            "800x600+100+100",
        )

    def test_oversized_window_is_capped_to_the_screen(self):
        clamped = AutoClicker._clamp_geometry_to_screen("5000x4000+0+0", 1920, 1080)
        self.assertTrue(clamped.startswith("1920x1080"))

    def test_unparseable_geometry_passes_through(self):
        self.assertEqual(AutoClicker._clamp_geometry_to_screen("garbage", 1920, 1080), "garbage")


class SystemThemeTests(unittest.TestCase):
    def test_light_and_dark_are_derived_from_the_reader(self):
        self.assertEqual(AutoClicker._detect_system_theme(lambda: 1), "Light")
        self.assertEqual(AutoClicker._detect_system_theme(lambda: 0), "Dark")

    def test_a_failing_reader_falls_back_to_light(self):
        def boom():
            raise OSError("no registry")

        self.assertEqual(AutoClicker._detect_system_theme(boom), "Light")


class ReadinessTests(unittest.TestCase):
    def _config(self, **overrides):
        config = {
            "x": 100, "y": 100, "delay": 0.1, "runtime_limit": 0, "max_actions": 10,
            "repeat_limit": None, "stop_hotkey": "esc", "dry_run": True,
            "pyautogui_failsafe": True, "click_mode": "Left Click", "pacing_mode": "Precise",
        }
        config.update(overrides)
        return config

    def _item(self, readiness, label):
        return next(item for item in readiness["items"] if item["label"] == label)

    def test_an_unpollable_stop_hotkey_is_flagged_not_reported_green(self):
        readiness = AutoClicker._build_readiness_checklist(self._config(stop_hotkey="ctrl, k"))
        self.assertEqual(self._item(readiness, "Stop hotkey")["state"], "review")
        self.assertFalse(readiness["ready"])

    def test_legacy_pacing_warns_that_the_real_rate_differs(self):
        readiness = AutoClicker._build_readiness_checklist(
            self._config(pacing_mode="Legacy V10.1")
        )
        self.assertEqual(self._item(readiness, "Pace")["state"], "review")

    def test_precise_pacing_reports_the_promised_rate(self):
        readiness = AutoClicker._build_readiness_checklist(self._config())
        pace = self._item(readiness, "Pace")
        self.assertEqual(pace["state"], "ok")
        self.assertIn("10.0 action(s)/sec", pace["detail"])

    def test_a_misconfigured_action_is_flagged(self):
        readiness = AutoClicker._build_readiness_checklist(
            self._config(click_mode="Key Press", action_key="")
        )
        self.assertEqual(self._item(readiness, "Action")["state"], "review")

    def test_round_robin_targets_are_reported(self):
        readiness = AutoClicker._build_readiness_checklist(
            self._config(targets=[(1, 2), (3, 4), (5, 6)])
        )
        self.assertIn("3 recorded point(s)", self._item(readiness, "Targets")["detail"])

    def test_a_clean_config_is_ready(self):
        self.assertTrue(AutoClicker._build_readiness_checklist(self._config())["ready"])


if __name__ == "__main__":
    unittest.main()
