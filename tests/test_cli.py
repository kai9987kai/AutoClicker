"""End-to-end tests for the headless command line.

These run AutoClicker.py as a subprocess so they pin the real exit-code contract:
0 success, 1 check/validation failure, 2 usage error, 3 internal error.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

import AutoClicker

SCRIPT = os.path.abspath(AutoClicker.__file__)
REPO_ROOT = os.path.dirname(SCRIPT)


def run_cli(*args, state_dir=None):
    env = dict(os.environ)
    if state_dir:
        env["APPDATA"] = state_dir
        env["LOCALAPPDATA"] = state_dir
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=120,
    )


class CliContractTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.state_dir = self._temp.name
        self.addCleanup(self._temp.cleanup)

    def write(self, name, payload):
        path = os.path.join(self.state_dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            if isinstance(payload, str):
                handle.write(payload)
            else:
                json.dump(payload, handle)
        return path

    def test_help_prints_usage_and_does_not_open_the_gui(self):
        result = run_cli("--help", state_dir=self.state_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: AutoClicker", result.stdout)

    def test_version_reports_the_app_version(self):
        result = run_cli("--version", state_dir=self.state_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn(AutoClicker.APP_VERSION, result.stdout)

    def test_unknown_flag_is_a_usage_error_not_a_gui_launch(self):
        # V10.1 fell through to MAINWINDOW_REDESIGNED() for anything unrecognised,
        # so a typo on a headless runner tried to open a window.
        result = run_cli("--not-a-real-flag", state_dir=self.state_dir)
        self.assertEqual(result.returncode, 2)

    def test_unknown_subcommand_is_a_usage_error(self):
        self.assertEqual(run_cli("nonsense", state_dir=self.state_dir).returncode, 2)

    def test_missing_required_path_is_a_usage_error(self):
        self.assertEqual(run_cli("validate-recording", state_dir=self.state_dir).returncode, 2)

    def test_health_reports_dependencies(self):
        result = run_cli("health", state_dir=self.state_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("AutoClicker Health Check", result.stdout)

    def test_health_json_uses_the_shared_envelope(self):
        result = run_cli("health", "--json", state_dir=self.state_dir)
        payload = json.loads(result.stdout)
        for key in ("schema_version", "app_version", "command", "ok", "generated_at", "data", "errors"):
            self.assertIn(key, payload)
        self.assertEqual(payload["command"], "health")
        self.assertTrue(payload["ok"])

    def test_doctor_prints_an_actionable_install_line(self):
        result = run_cli("doctor", state_dir=self.state_dir)
        self.assertIn("Doctor", result.stdout)

    def test_schema_command_describes_every_action(self):
        result = run_cli("schema", "action", "--json", state_dir=self.state_dir)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload["data"]["actions"]), set(AutoClicker.ACTION_REGISTRY))

    def test_state_summary_still_works(self):
        self.assertEqual(run_cli("state-summary", state_dir=self.state_dir).returncode, 0)

    def test_backup_dry_run_writes_nothing(self):
        before = set(os.listdir(self.state_dir))
        result = run_cli("backup-state", "--dry-run", state_dir=self.state_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Dry run", result.stdout)
        self.assertEqual(set(os.listdir(self.state_dir)), before)

    def test_valid_recording_exits_zero(self):
        path = self.write("rec.json", [[10, 20], [30, 40]])
        result = run_cli("validate-recording", path, state_dir=self.state_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("2 point(s)", result.stdout)

    def test_invalid_recording_exits_one(self):
        path = self.write("bad.json", "not json at all")
        self.assertEqual(run_cli("validate-recording", path, state_dir=self.state_dir).returncode, 1)

    def test_sequences_may_use_the_new_action_vocabulary(self):
        path = self.write("seq.json", [[1, 2, "Left Click", 0.5], [3, 4, "Scroll Down", 0.25]])
        result = run_cli("validate-sequence", path, state_dir=self.state_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("2 step(s)", result.stdout)

    def test_multiple_paths_are_all_validated(self):
        good = self.write("rec.json", [[1, 2]])
        bad = self.write("bad.json", "nope")
        result = run_cli("validate-recording", good, bad, state_dir=self.state_dir)
        self.assertEqual(result.returncode, 1)
        payload_result = run_cli("validate-recording", good, bad, "--json", state_dir=self.state_dir)
        payload = json.loads(payload_result.stdout)
        self.assertEqual(payload["data"]["count"], 2)
        self.assertFalse(payload["ok"])

    def test_legacy_flags_still_work(self):
        recording = self.write("rec.json", [[1, 2]])
        cases = [
            (("--health-check",), 0),
            (("--health-json",), 0),
            (("--state-summary",), 0),
            (("--state-json",), 0),
            (("--validate-recording", recording), 0),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(run_cli(*args, state_dir=self.state_dir).returncode, expected)

    def test_legacy_gnu_equals_form_is_understood(self):
        # "--validate-recording=x.json" is one argv token, which V10.1 did not match,
        # so it silently launched the GUI instead of validating.
        recording = self.write("rec.json", [[1, 2]])
        result = run_cli(f"--validate-recording={recording}", state_dir=self.state_dir)
        self.assertEqual(result.returncode, 0)

    def test_stacked_legacy_flags_no_longer_hide_a_failure(self):
        # V10.1 answered the first flag only and exited 0, so a failing validation
        # combined with a logging flag reported success.
        bad = self.write("bad.json", "nope")
        result = run_cli("--validate-recording", bad, "--state-summary", state_dir=self.state_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Ignored extra legacy flag", result.stderr)

    def test_health_strict_fails_when_a_required_dependency_is_missing(self):
        result = run_cli("health", "--strict", "--json", state_dir=self.state_dir)
        payload = json.loads(result.stdout)
        missing = payload["data"]["missing_required"]
        self.assertEqual(result.returncode, 1 if missing else 0)

    def test_profiles_list_and_show(self):
        os.makedirs(os.path.join(self.state_dir, "AutoClicker"), exist_ok=True)
        profiles_path = os.path.join(self.state_dir, "AutoClicker", AutoClicker.PROFILE_FILE_NAME)
        with open(profiles_path, "w", encoding="utf-8") as handle:
            json.dump({"gaming": {"delay": "0.05", "click_mode": "Left Click", "stop_hotkey": "esc"}}, handle)

        listed = run_cli("profiles", "--json", state_dir=self.state_dir)
        self.assertEqual(listed.returncode, 0)
        self.assertEqual(json.loads(listed.stdout)["data"]["names"], ["gaming"])

        shown = run_cli("profiles", "gaming", state_dir=self.state_dir)
        self.assertEqual(shown.returncode, 0)
        self.assertIn("delay", shown.stdout)

        missing = run_cli("profiles", "nope", state_dir=self.state_dir)
        self.assertEqual(missing.returncode, 1)

    def test_readiness_checks_a_saved_profile_without_a_display(self):
        os.makedirs(os.path.join(self.state_dir, "AutoClicker"), exist_ok=True)
        profiles_path = os.path.join(self.state_dir, "AutoClicker", AutoClicker.PROFILE_FILE_NAME)
        with open(profiles_path, "w", encoding="utf-8") as handle:
            json.dump({
                "risky": {
                    "delay": "0", "click_mode": "Left Click", "stop_hotkey": "",
                    "repeat_mode": "Infinite", "max_actions": "0", "runtime_limit": "0",
                },
            }, handle)
        result = run_cli("readiness", "risky", "--json", state_dir=self.state_dir)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["data"]["readiness"]["ready"])
        self.assertEqual(result.returncode, 1)

    def test_history_is_empty_on_a_fresh_state_dir(self):
        result = run_cli("history", "--json", state_dir=self.state_dir)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["data"]["summary"]["runs"], 0)


class LegacyTranslationTests(unittest.TestCase):
    """Unit-level checks on argument translation (no subprocess)."""

    def test_no_arguments_stay_empty(self):
        self.assertEqual(AutoClicker._translate_legacy_args([]), ([], []))

    def test_modern_arguments_pass_through_untouched(self):
        args = ["health", "--json"]
        self.assertEqual(AutoClicker._translate_legacy_args(args), (args, []))

    def test_legacy_flag_maps_to_a_subcommand(self):
        translated, ignored = AutoClicker._translate_legacy_args(["--health-json"])
        self.assertEqual(translated, ["health", "--json"])
        self.assertEqual(ignored, [])

    def test_legacy_flag_with_a_value(self):
        translated, _ = AutoClicker._translate_legacy_args(["--validate-recording", "a.json"])
        self.assertEqual(translated, ["validate-recording", "a.json"])

    def test_extra_legacy_flags_are_reported_not_dropped(self):
        translated, ignored = AutoClicker._translate_legacy_args(
            ["--validate-recording", "a.json", "--state-summary"]
        )
        self.assertEqual(translated, ["validate-recording", "a.json"])
        self.assertEqual(ignored, ["--state-summary"])


class SchemaDescriptionTests(unittest.TestCase):
    def test_every_schema_kind_is_describable(self):
        for kind in ("recording", "sequence", "profile", "action"):
            with self.subTest(kind=kind):
                described = AutoClicker._describe_schema(kind)
                self.assertEqual(described["kind"], kind)
                self.assertTrue(described["description"])

    def test_profile_schema_lists_the_real_field_sets(self):
        described = AutoClicker._describe_schema("profile")
        self.assertEqual(set(described["fields"]), AutoClicker.PROFILE_FIELDS)

    def test_readiness_projection_handles_an_empty_profile(self):
        config = AutoClicker._readiness_config_from_profile({})
        self.assertEqual(config["x"], 0)
        self.assertIsNone(config["repeat_limit"])

    def test_readiness_projection_reads_burst_counts(self):
        config = AutoClicker._readiness_config_from_profile(
            {"repeat_mode": "Burst Count", "repeat_count": "25"}
        )
        self.assertEqual(config["repeat_limit"], 25)

    def test_readiness_projection_survives_garbage_values(self):
        config = AutoClicker._readiness_config_from_profile(
            {"target_x": "abc", "delay": None, "repeat_mode": "Burst Count", "repeat_count": "xyz"}
        )
        self.assertEqual(config["x"], 0)
        self.assertEqual(config["delay"], 0.0)
        self.assertIsNone(config["repeat_limit"])


if __name__ == "__main__":
    unittest.main()
