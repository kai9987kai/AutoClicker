import json
import os
import tempfile
import unittest
from unittest import mock

import AutoClicker


class HelperTests(unittest.TestCase):
    def test_format_seconds_uses_readable_units(self):
        self.assertEqual(AutoClicker._format_seconds(12.345), "12.35s")
        self.assertEqual(AutoClicker._format_seconds(75), "1m 15s")
        self.assertEqual(AutoClicker._format_seconds(3661), "1h 01m 01s")

    def test_atomic_write_json_replaces_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "state.json")
            AutoClicker._atomic_write_json(path, {"before": True})
            AutoClicker._atomic_write_json(path, {"after": [1, 2, 3]}, sort_keys=True)

            with open(path, "r", encoding="utf-8") as file_handle:
                self.assertEqual(json.load(file_handle), {"after": [1, 2, 3]})
            self.assertFalse(os.path.exists(f"{path}.tmp"))

    def test_state_file_uses_appdata_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}, clear=False):
                state_path = AutoClicker._state_file_path("sample.json")

            self.assertEqual(os.path.dirname(state_path), os.path.join(temp_dir, "AutoClicker"))
            self.assertTrue(os.path.isdir(os.path.dirname(state_path)))

    def test_headless_health_report_has_core_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}, clear=False):
                report = AutoClicker._build_headless_health_report()

            self.assertIn("AutoClicker Health Check", report)
            self.assertIn(f"App version: {AutoClicker.APP_VERSION}", report)
            self.assertIn("Dependencies", report)
            self.assertIn("State Files", report)

    def test_headless_health_data_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}, clear=False):
                data = AutoClicker._collect_headless_health_data()

            self.assertEqual(data["app_version"], AutoClicker.APP_VERSION)
            self.assertIn("dependencies", data)
            self.assertIn("profiles", data["state_files"])
            self.assertEqual(
                data["state_files"]["profiles"]["path"],
                os.path.join(temp_dir, "AutoClicker", "autoclicker_profiles.json"),
            )
            self.assertFalse(os.path.exists(os.path.join(temp_dir, "AutoClicker")))

    def test_session_report_payload_keeps_recent_entries(self):
        profile_data = {"dry_run": True, "delay": "0.1"}
        activities = [f"activity {index}" for index in range(100)]
        reports = [{"actions": index} for index in range(50)]

        payload = AutoClicker._build_session_report_payload(
            profile_data,
            activities,
            reports,
            {"workspace": "workspace.json"},
        )

        self.assertEqual(payload["app_version"], AutoClicker.APP_VERSION)
        self.assertEqual(payload["profile_data"], profile_data)
        self.assertEqual(len(payload["activity_history"]), 80)
        self.assertEqual(payload["activity_history"][0], "activity 20")
        self.assertEqual(len(payload["run_reports"]), 40)
        self.assertEqual(payload["run_reports"][0], {"actions": 10})
        self.assertEqual(payload["state_files"]["workspace"], "workspace.json")

    def test_recording_point_normalization(self):
        raw_points = [[index, str(index + 1)] for index in range(205)]

        points = AutoClicker._normalize_recording_points(raw_points)

        self.assertEqual(len(points), 200)
        self.assertEqual(points[0], (5, 6))
        self.assertEqual(points[-1], (204, 205))

    def test_recording_point_normalization_rejects_bad_shape(self):
        with self.assertRaisesRegex(ValueError, "Point 1 is invalid"):
            AutoClicker._normalize_recording_points([[1, 2, 3]])

    def test_sequence_step_normalization(self):
        steps = AutoClicker._normalize_sequence_steps([["10", "20", "Left Click", "0.25"]])

        self.assertEqual(steps, [(10, 20, "Left Click", 0.25)])

    def test_sequence_step_normalization_rejects_unknown_action(self):
        with self.assertRaisesRegex(ValueError, "unknown action"):
            AutoClicker._normalize_sequence_steps([[10, 20, "Side Click", 0.1]])

    def test_state_summary_counts_existing_files_without_creating_missing_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = os.path.join(temp_dir, "AutoClicker")
            os.makedirs(state_dir)
            AutoClicker._atomic_write_json(
                os.path.join(state_dir, "autoclicker_profiles.json"),
                {"default": {"delay": "0.1"}},
            )
            AutoClicker._atomic_write_json(
                os.path.join(state_dir, "autoclicker_workspace.json"),
                {
                    "profile_data": {"delay": "0.1"},
                    "recording_data": [[1, 2], [3, 4]],
                    "activity_history": ["one"],
                    "run_reports": [{"actions": 2}],
                },
            )

            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}, clear=False):
                summary = AutoClicker._collect_state_summary_data()

            self.assertEqual(summary["profiles"]["count"], 1)
            self.assertEqual(summary["workspace"]["recording_points"], 2)
            self.assertEqual(summary["workspace"]["activity_entries"], 1)
            self.assertEqual(summary["workspace"]["run_reports"], 1)
            self.assertTrue(summary["workspace"]["has_profile_data"])

    def test_state_backup_copies_raw_state_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = os.path.join(temp_dir, "AutoClicker")
            backup_dir = os.path.join(temp_dir, "backup")
            os.makedirs(state_dir)
            profile_path = os.path.join(state_dir, "autoclicker_profiles.json")
            workspace_path = os.path.join(state_dir, "autoclicker_workspace.json")
            with open(profile_path, "w", encoding="utf-8") as file_handle:
                file_handle.write('{"default": true}')
            with open(workspace_path, "w", encoding="utf-8") as file_handle:
                file_handle.write("{not valid json")

            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}, clear=False):
                with mock.patch("AutoClicker.os.getcwd", return_value=os.path.join(temp_dir, "cwd")):
                    result = AutoClicker._backup_state_files(backup_dir)

            self.assertEqual(result["count"], 2)
            self.assertTrue(os.path.exists(os.path.join(backup_dir, "manifest.json")))
            with open(os.path.join(backup_dir, "autoclicker_profiles.json"), "r", encoding="utf-8") as file_handle:
                self.assertEqual(file_handle.read(), '{"default": true}')
            with open(os.path.join(backup_dir, "autoclicker_workspace.json"), "r", encoding="utf-8") as file_handle:
                self.assertEqual(file_handle.read(), "{not valid json")
            with open(os.path.join(backup_dir, "manifest.json"), "r", encoding="utf-8") as file_handle:
                manifest = json.load(file_handle)
            self.assertEqual(manifest["count"], 2)
            self.assertIn("state_summary", manifest)

    def test_profile_validation_accepts_known_fields_and_warns_unknown(self):
        result = AutoClicker._validate_profile_data(
            "default",
            {
                "target_x": "10",
                "target_y": 20,
                "click_mode": "Left Click",
                "repeat_mode": "Burst Count",
                "repeat_count": "3",
                "delay": "0.15",
                "dry_run": True,
                "future_field": "kept",
            },
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["unknown_fields"], ["future_field"])
        self.assertIn("unknown fields: future_field", result["warnings"])

    def test_profile_validation_rejects_bad_known_fields(self):
        result = AutoClicker._validate_profile_data(
            "bad",
            {
                "click_mode": "Side Click",
                "delay": "-1",
                "repeat_count": "0",
            },
        )

        self.assertFalse(result["valid"])
        self.assertIn("delay must be zero or greater", result["errors"])
        self.assertIn("repeat_count must be at least 1", result["errors"])
        self.assertTrue(any("click_mode must be one of" in error for error in result["errors"]))

    def test_profile_import_preview_counts_valid_invalid_and_overwrites(self):
        preview = AutoClicker._preview_profile_import(
            {
                "existing": {"delay": "0.1"},
                "new": {"click_mode": "Right Click"},
                "bad": {"runtime_limit": "-1"},
            },
            existing_profiles={"existing": {"delay": "0.2"}},
        )

        self.assertEqual(preview["valid_count"], 2)
        self.assertEqual(preview["invalid_count"], 1)
        self.assertEqual(preview["overwrite_count"], 1)
        self.assertEqual(preview["new_count"], 1)
        self.assertIn("existing", preview["overwrites"])
        self.assertIn("new", preview["new_profiles"])

    def test_readiness_checklist_is_ready_for_guarded_bounded_run(self):
        readiness = AutoClicker._build_readiness_checklist(
            {
                "x": 100,
                "y": 200,
                "dry_run": False,
                "pyautogui_failsafe": True,
                "repeat_limit": None,
                "runtime_limit": 0,
                "max_actions": 25,
                "delay": 0.1,
                "stop_hotkey": "esc",
            },
            screen_size=(1920, 1080),
        )

        self.assertTrue(readiness["ready"])
        self.assertEqual(readiness["review_count"], 0)
        self.assertEqual(readiness["status"], "Ready")

    def test_readiness_checklist_flags_risky_unbounded_run(self):
        readiness = AutoClicker._build_readiness_checklist(
            {
                "x": 5000,
                "y": -20,
                "dry_run": False,
                "pyautogui_failsafe": False,
                "repeat_limit": None,
                "runtime_limit": 0,
                "max_actions": 0,
                "delay": 0,
                "stop_hotkey": "",
            },
            screen_size=(1920, 1080),
        )

        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["review_count"], 5)
        self.assertIn("Review 5 item(s)", AutoClicker._format_readiness_text(readiness))

    def test_safety_presets_include_guarded_modes(self):
        self.assertTrue(AutoClicker.SAFETY_PRESETS["Simulation"]["dry_run"])
        self.assertTrue(AutoClicker.SAFETY_PRESETS["Guarded Live"]["pyautogui_failsafe"])
        self.assertEqual(AutoClicker.SAFETY_PRESETS["Manual Stop Live"]["max_actions"], "0")

    def test_profile_state_reports_saved_modified_new_and_missing(self):
        saved_profiles = {"default": {"delay": "0.1", "dry_run": True}}

        saved = AutoClicker._build_profile_state(
            "default",
            "default",
            {"delay": "0.1", "dry_run": True},
            saved_profiles,
        )
        modified = AutoClicker._build_profile_state(
            "default",
            "default",
            {"delay": "0.2", "dry_run": True},
            saved_profiles,
        )
        new = AutoClicker._build_profile_state("new", "", {"delay": "0.1"}, saved_profiles)
        missing = AutoClicker._build_profile_state("", "", {"delay": "0.1"}, saved_profiles)

        self.assertEqual(saved["state"], "saved")
        self.assertEqual(modified["state"], "modified")
        self.assertEqual(new["state"], "new")
        self.assertEqual(missing["state"], "review")
        self.assertIn("Modified", AutoClicker._format_profile_state_text(modified))

    def test_support_bundle_writes_known_reports_and_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = os.path.join(temp_dir, "AutoClicker")
            bundle_dir = os.path.join(temp_dir, "bundle")
            os.makedirs(state_dir)
            AutoClicker._atomic_write_json(
                os.path.join(state_dir, "autoclicker_workspace.json"),
                {"activity_history": ["one"], "run_reports": []},
            )

            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}, clear=False):
                with mock.patch("AutoClicker.os.getcwd", return_value=os.path.join(temp_dir, "cwd")):
                    result = AutoClicker._build_support_bundle(
                        bundle_dir,
                        profile_data={"dry_run": True},
                        activity_history=["one"],
                        run_reports=[{"actions": 1}],
                        state_files={"workspace": "workspace.json"},
                    )

            self.assertTrue(os.path.exists(result["manifest_path"]))
            self.assertTrue(os.path.exists(result["files"]["health_report"]))
            self.assertTrue(os.path.exists(result["files"]["session_report"]))
            self.assertEqual(result["backup"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
