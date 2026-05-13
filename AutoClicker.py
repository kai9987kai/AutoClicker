import time
import tkinter as tk
import webbrowser
from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
import os
import sys
import datetime
import threading
import queue
import json
import random
import math
import platform
import warnings
import shutil

IMPORT_ERRORS = {}
APP_VERSION = "V10.1"
APP_STATE_DIR_NAME = "AutoClicker"
PROFILE_FILE_NAME = "autoclicker_profiles.json"
WORKSPACE_FILE_NAME = "autoclicker_workspace.json"
DEFAULT_CLICK_TYPES = {
    "Left Click": ("left", 1),
    "Right Click": ("right", 1),
    "Middle Click": ("middle", 1),
    "Double Left Click": ("left", 2),
    "Double Right Click": ("right", 2),
    "Double Middle Click": ("middle", 2),
}
PROFILE_FIELDS = {
    "target_x",
    "target_y",
    "click_mode",
    "delay",
    "delay_variance",
    "jitter_x",
    "jitter_y",
    "countdown",
    "runtime_limit",
    "max_actions",
    "stop_hotkey",
    "repeat_mode",
    "repeat_count",
    "behaviour_preset",
    "micro_pause_every",
    "micro_pause_duration",
    "topmost",
    "minimize_on_start",
    "restore_after_run",
    "close_to_tray",
    "fullscreen",
    "remember_window_geometry",
    "window_opacity",
    "ui_scale",
    "human_like",
    "play_sound",
    "dry_run",
    "pyautogui_failsafe",
    "theme",
}
PROFILE_INT_FIELDS = {
    "target_x",
    "target_y",
    "jitter_x",
    "jitter_y",
    "max_actions",
    "micro_pause_every",
    "repeat_count",
}
PROFILE_FLOAT_FIELDS = {
    "delay",
    "delay_variance",
    "countdown",
    "runtime_limit",
    "micro_pause_duration",
    "window_opacity",
    "ui_scale",
}
PROFILE_BOOL_FIELDS = {
    "topmost",
    "minimize_on_start",
    "restore_after_run",
    "close_to_tray",
    "fullscreen",
    "remember_window_geometry",
    "human_like",
    "play_sound",
    "dry_run",
    "pyautogui_failsafe",
}
PROFILE_ENUM_FIELDS = {
    "click_mode": set(DEFAULT_CLICK_TYPES),
    "repeat_mode": {"Infinite", "Burst Count"},
    "behaviour_preset": {"Balanced", "Precision", "Burst Sprint", "Human Mimic"},
    "theme": {"Light", "Dark", "Ocean"},
}
SAFETY_PRESETS = {
    "Simulation": {
        "dry_run": True,
        "pyautogui_failsafe": True,
        "max_actions": "25",
    },
    "Guarded Live": {
        "dry_run": False,
        "pyautogui_failsafe": True,
        "max_actions": "250",
    },
    "Manual Stop Live": {
        "dry_run": False,
        "pyautogui_failsafe": True,
        "max_actions": "0",
    },
}


def _resource_path(file_name):
    """Resolve bundled resources from source checkouts and PyInstaller builds."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    search_roots = [
        bundle_root,
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
    ]
    for root in search_roots:
        if not root:
            continue
        candidate = os.path.join(root, file_name)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(os.getcwd(), file_name)


def _state_dir():
    state_root = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if state_root:
        return os.path.join(state_root, APP_STATE_DIR_NAME)
    return os.getcwd()


def _state_file_location(file_name):
    return os.path.join(_state_dir(), file_name)


def _copy_legacy_state_file(file_name, destination):
    legacy_path = os.path.join(os.getcwd(), file_name)
    if os.path.abspath(legacy_path) == os.path.abspath(destination):
        return
    if not os.path.exists(legacy_path) or os.path.exists(destination):
        return

    try:
        with open(legacy_path, "r", encoding="utf-8") as source_handle:
            legacy_contents = source_handle.read()
        with open(destination, "w", encoding="utf-8") as destination_handle:
            destination_handle.write(legacy_contents)
    except Exception:
        pass


def _state_file_path(file_name):
    directory = _state_dir()
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception:
        directory = os.getcwd()

    destination = os.path.join(directory, file_name)
    _copy_legacy_state_file(file_name, destination)
    return destination


def _atomic_write_json(path, payload, sort_keys=False):
    directory = os.path.dirname(path) or os.getcwd()
    os.makedirs(directory, exist_ok=True)
    temp_path = f"{path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2, sort_keys=sort_keys)
        os.replace(temp_path, path)
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise


def _format_seconds(seconds):
    try:
        seconds = float(seconds)
    except Exception:
        return "unknown"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes, remainder = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes}m {remainder:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m {remainder:02d}s"


def _build_readiness_checklist(config, screen_size=None):
    items = []

    def add(label, state, detail):
        items.append({"label": label, "state": state, "detail": detail})

    x_pos = int(config.get("x", 0))
    y_pos = int(config.get("y", 0))
    if screen_size:
        screen_width, screen_height = screen_size
        if 0 <= x_pos < screen_width and 0 <= y_pos < screen_height:
            add("Target", "ok", f"{x_pos}, {y_pos} is inside the screen.")
        else:
            clamped_x = max(0, min(screen_width - 1, x_pos))
            clamped_y = max(0, min(screen_height - 1, y_pos))
            add("Target", "review", f"{x_pos}, {y_pos} is outside the screen; run clamps to {clamped_x}, {clamped_y}.")
    else:
        add("Target", "ok", f"{x_pos}, {y_pos} configured.")

    if config.get("dry_run"):
        add("Output", "ok", "Dry run is on; no clicks will be sent.")
    else:
        add("Output", "ok", "Live click output is enabled.")

    if config.get("pyautogui_failsafe"):
        add("Fail-safe", "ok", "PyAutoGUI corner fail-safe is enabled.")
    else:
        add("Fail-safe", "review", "Corner fail-safe is off.")

    repeat_limit = config.get("repeat_limit")
    runtime_limit = float(config.get("runtime_limit", 0))
    max_actions = int(config.get("max_actions", 0))
    if repeat_limit is not None:
        add("Stop boundary", "ok", f"Burst count stops after {repeat_limit} action(s).")
    elif runtime_limit > 0:
        add("Stop boundary", "ok", f"Runtime cap stops after {_format_seconds(runtime_limit)}.")
    elif max_actions > 0:
        add("Stop boundary", "ok", f"Max action cap stops after {max_actions} action(s).")
    else:
        add("Stop boundary", "review", "No runtime or action cap is set.")

    delay = float(config.get("delay", 0))
    if delay == 0:
        add("Pace", "review", "Zero delay uses maximum available pace.")
    else:
        add("Pace", "ok", f"Base delay is {_format_seconds(delay)}.")

    if config.get("stop_hotkey"):
        add("Stop hotkey", "ok", f"Stop hotkey is {config['stop_hotkey']}.")
    elif repeat_limit is None and runtime_limit == 0 and max_actions == 0:
        add("Stop hotkey", "review", "Continuous run has no stop hotkey.")

    review_count = sum(1 for item in items if item["state"] == "review")
    status = "Ready" if review_count == 0 else f"Review {review_count} item(s)"
    return {
        "ready": review_count == 0,
        "status": status,
        "review_count": review_count,
        "items": items,
    }


def _format_readiness_text(readiness, limit=6):
    lines = [f"Readiness: {readiness['status']}"]
    for item in readiness["items"][:limit]:
        prefix = "OK" if item["state"] == "ok" else "Review"
        lines.append(f"- {prefix} {item['label']}: {item['detail']}")
    remaining = len(readiness["items"]) - limit
    if remaining > 0:
        lines.append(f"- +{remaining} more check(s)")
    return "\n".join(lines)


def _profile_payload_key(profile_data):
    try:
        return json.dumps(profile_data or {}, sort_keys=True, default=str)
    except Exception:
        return repr(profile_data)


def _build_profile_state(profile_name, profile_choice, current_profile, saved_profiles):
    profile_name = str(profile_name or "").strip()
    profile_choice = str(profile_choice or "").strip()
    saved_profiles = saved_profiles if isinstance(saved_profiles, dict) else {}

    if not profile_name and not profile_choice:
        return {
            "state": "review",
            "profile_name": "",
            "profile_choice": "",
            "detail": "Enter a profile name before saving this setup.",
        }

    active_name = profile_name or profile_choice
    saved_profile = saved_profiles.get(active_name)
    selection_note = ""
    if profile_name and profile_choice and profile_name != profile_choice:
        selection_note = f" Selected profile is '{profile_choice}'."

    if saved_profile is None:
        return {
            "state": "new",
            "profile_name": active_name,
            "profile_choice": profile_choice,
            "detail": f"'{active_name}' is not saved yet.{selection_note}",
        }

    if _profile_payload_key(current_profile) == _profile_payload_key(saved_profile):
        return {
            "state": "saved",
            "profile_name": active_name,
            "profile_choice": profile_choice,
            "detail": f"'{active_name}' matches the saved profile.{selection_note}",
        }

    return {
        "state": "modified",
        "profile_name": active_name,
        "profile_choice": profile_choice,
        "detail": f"'{active_name}' has unsaved changes.{selection_note}",
    }


def _format_profile_state_text(profile_state):
    labels = {
        "saved": "Saved",
        "modified": "Modified",
        "new": "New",
        "review": "Review",
    }
    label = labels.get(profile_state.get("state"), "Profile")
    return f"Profile: {label} - {profile_state.get('detail', '')}"

try:
    import pystray
    from pystray import MenuItem as item
except Exception as exc:
    pystray = None
    item = None
    IMPORT_ERRORS["pystray"] = str(exc)

try:
    import pyautogui
except Exception as exc:
    pyautogui = None
    IMPORT_ERRORS["pyautogui"] = str(exc)

try:
    import keyboard
except Exception as exc:
    keyboard = None
    IMPORT_ERRORS["keyboard"] = str(exc)

try:
    from PIL import Image, ImageTk, ImageGrab
except Exception as exc:
    Image = None
    ImageTk = None
    ImageGrab = None
    IMPORT_ERRORS["Pillow"] = str(exc)

try:
    import winsound
except ImportError:
    winsound = None


def _collect_headless_health_data():
    import importlib.util

    dependency_names = {
        "pyautogui": "pyautogui",
        "keyboard": "keyboard",
        "pystray": "pystray",
        "Pillow": "PIL",
        "numpy": "numpy",
        "pywin32": "win32api",
    }
    dependencies = {}
    for dependency_name, module_name in dependency_names.items():
        if dependency_name in IMPORT_ERRORS:
            dependencies[dependency_name] = {
                "available": False,
                "detail": IMPORT_ERRORS[dependency_name],
            }
        elif importlib.util.find_spec(module_name) is None:
            dependencies[dependency_name] = {
                "available": False,
                "detail": "module not found",
            }
        else:
            dependencies[dependency_name] = {
                "available": True,
                "detail": "available",
            }

    profile_file = _state_file_location(PROFILE_FILE_NAME)
    workspace_file = _state_file_location(WORKSPACE_FILE_NAME)
    return {
        "app_version": APP_VERSION,
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "resource_root": os.path.dirname(_resource_path("favicon.ico")),
        "dependencies": dependencies,
        "state_files": {
            "profiles": {
                "path": profile_file,
                "present": os.path.exists(profile_file),
            },
            "workspace": {
                "path": workspace_file,
                "present": os.path.exists(workspace_file),
            },
        },
    }


def _build_headless_health_report():
    health_data = _collect_headless_health_data()
    dependency_lines = []
    for dependency_name, dependency_data in health_data["dependencies"].items():
        if dependency_data["available"]:
            dependency_lines.append(f"- {dependency_name}: available")
        else:
            dependency_lines.append(f"- {dependency_name}: missing ({dependency_data['detail']})")

    profile_file = health_data["state_files"]["profiles"]
    workspace_file = health_data["state_files"]["workspace"]
    sections = [
        "AutoClicker Health Check",
        f"- App version: {health_data['app_version']}",
        f"- OS: {health_data['os']}",
        f"- Python: {health_data['python']}",
        f"- Resource root: {health_data['resource_root']}",
        "",
        "Dependencies",
        *dependency_lines,
        "",
        "State Files",
        f"- Profiles file: {'present' if profile_file['present'] else 'not created yet'}",
        f"  {profile_file['path']}",
        f"- Workspace file: {'present' if workspace_file['present'] else 'not created yet'}",
        f"  {workspace_file['path']}",
    ]
    return "\n".join(sections)


def _build_session_report_payload(profile_data, activity_history, run_reports, state_files=None):
    return {
        "app_version": APP_VERSION,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "platform": {
            "os": f"{platform.system()} {platform.release()}",
            "python": sys.version.split()[0],
        },
        "profile_data": dict(profile_data),
        "activity_history": [str(entry) for entry in activity_history[-80:]],
        "run_reports": list(run_reports[-40:]),
        "state_files": dict(state_files or {}),
    }


def _file_info(path):
    present = os.path.exists(path)
    info = {
        "path": path,
        "present": present,
        "size_bytes": 0,
        "modified_at": None,
    }
    if present:
        try:
            stat_result = os.stat(path)
            info["size_bytes"] = stat_result.st_size
            info["modified_at"] = datetime.datetime.fromtimestamp(stat_result.st_mtime).isoformat(timespec="seconds")
        except Exception as exc:
            info["error"] = str(exc)
    return info


def _load_json_file(path):
    with open(path, "r", encoding="utf-8-sig") as file_handle:
        return json.load(file_handle)


def _normalize_recording_points(raw_points, limit=200, strict=True):
    if not isinstance(raw_points, list):
        raise ValueError("Recording files must contain a list of coordinate pairs.")

    cleaned_points = []
    for index, point in enumerate(raw_points, start=1):
        try:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError("expected [x, y]")
            cleaned_points.append((int(point[0]), int(point[1])))
        except Exception as exc:
            if strict:
                raise ValueError(f"Point {index} is invalid: {exc}") from exc

    return cleaned_points[-limit:]


def _normalize_sequence_steps(raw_steps, click_types=None):
    click_types = click_types or DEFAULT_CLICK_TYPES
    if not isinstance(raw_steps, list):
        raise ValueError("Sequence files must contain a list of steps.")

    normalized_steps = []
    for index, step in enumerate(raw_steps, start=1):
        if not isinstance(step, (list, tuple)) or len(step) != 4:
            raise ValueError(f"Step {index} must contain X, Y, action, and delay.")
        try:
            x_pos = int(step[0])
            y_pos = int(step[1])
            action_name = str(step[2])
            delay_seconds = float(step[3])
        except Exception as exc:
            raise ValueError(f"Step {index} contains values that cannot be parsed: {exc}") from exc
        if action_name not in click_types:
            raise ValueError(f"Step {index} uses an unknown action: {action_name}.")
        if delay_seconds < 0:
            raise ValueError(f"Step {index} uses a negative delay.")
        normalized_steps.append((x_pos, y_pos, action_name, delay_seconds))
    return normalized_steps


def _collect_state_summary_data():
    profile_file = _state_file_location(PROFILE_FILE_NAME)
    workspace_file = _state_file_location(WORKSPACE_FILE_NAME)
    summary = {
        "app_version": APP_VERSION,
        "state_dir": os.path.dirname(profile_file),
        "profiles": {
            "file": _file_info(profile_file),
            "count": 0,
            "error": None,
        },
        "workspace": {
            "file": _file_info(workspace_file),
            "recording_points": 0,
            "activity_entries": 0,
            "run_reports": 0,
            "has_profile_data": False,
            "error": None,
        },
    }

    if summary["profiles"]["file"]["present"]:
        try:
            profile_data = _load_json_file(profile_file)
            if isinstance(profile_data, dict):
                summary["profiles"]["count"] = len(profile_data)
            else:
                summary["profiles"]["error"] = "profiles file is not a JSON object"
        except Exception as exc:
            summary["profiles"]["error"] = str(exc)

    if summary["workspace"]["file"]["present"]:
        try:
            workspace_data = _load_json_file(workspace_file)
            if isinstance(workspace_data, dict):
                summary["workspace"]["recording_points"] = len(workspace_data.get("recording_data") or [])
                summary["workspace"]["activity_entries"] = len(workspace_data.get("activity_history") or [])
                summary["workspace"]["run_reports"] = len(workspace_data.get("run_reports") or [])
                summary["workspace"]["has_profile_data"] = isinstance(workspace_data.get("profile_data"), dict)
            else:
                summary["workspace"]["error"] = "workspace file is not a JSON object"
        except Exception as exc:
            summary["workspace"]["error"] = str(exc)

    return summary


def _build_state_summary_report():
    summary = _collect_state_summary_data()
    profile_file = summary["profiles"]["file"]
    workspace_file = summary["workspace"]["file"]
    lines = [
        "AutoClicker State Summary",
        f"- App version: {summary['app_version']}",
        f"- State directory: {summary['state_dir']}",
        "",
        "Profiles",
        f"- File: {'present' if profile_file['present'] else 'not created yet'}",
        f"  {profile_file['path']}",
        f"- Saved profiles: {summary['profiles']['count']}",
    ]
    if summary["profiles"]["error"]:
        lines.append(f"- Error: {summary['profiles']['error']}")

    lines.extend(
        [
            "",
            "Workspace",
            f"- File: {'present' if workspace_file['present'] else 'not created yet'}",
            f"  {workspace_file['path']}",
            f"- Recording points: {summary['workspace']['recording_points']}",
            f"- Activity entries: {summary['workspace']['activity_entries']}",
            f"- Run reports: {summary['workspace']['run_reports']}",
            f"- Current profile data: {'present' if summary['workspace']['has_profile_data'] else 'not present'}",
        ]
    )
    if summary["workspace"]["error"]:
        lines.append(f"- Error: {summary['workspace']['error']}")
    return "\n".join(lines)


def _backup_state_files(destination_dir=None):
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if destination_dir is None:
        destination_dir = os.path.join(_state_dir(), "backups", timestamp)
    else:
        destination_dir = os.path.abspath(destination_dir)
    os.makedirs(destination_dir, exist_ok=True)

    copied_files = []
    copied_file_details = []
    seen_sources = set()
    for file_name in (PROFILE_FILE_NAME, WORKSPACE_FILE_NAME):
        candidates = [
            (_state_file_location(file_name), file_name),
            (os.path.join(os.getcwd(), file_name), f"legacy_{file_name}"),
        ]
        for source_path, backup_name in candidates:
            source_key = os.path.abspath(source_path)
            if source_key in seen_sources or not os.path.exists(source_path):
                continue
            seen_sources.add(source_key)
            destination_path = os.path.join(destination_dir, backup_name)
            shutil.copy2(source_path, destination_path)
            copied_files.append(destination_path)
            copied_file_details.append(
                {
                    "source": source_path,
                    "destination": destination_path,
                    "size_bytes": os.path.getsize(destination_path),
                }
            )

    result = {
        "app_version": APP_VERSION,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "backup_dir": destination_dir,
        "copied_files": copied_files,
        "copied_file_details": copied_file_details,
        "count": len(copied_files),
    }
    manifest_path = os.path.join(destination_dir, "manifest.json")
    result["manifest_path"] = manifest_path
    _atomic_write_json(
        manifest_path,
        {
            **result,
            "state_summary": _collect_state_summary_data(),
        },
        sort_keys=True,
    )
    return result


def _build_support_bundle(destination_dir=None, profile_data=None, activity_history=None, run_reports=None, state_files=None):
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if destination_dir is None:
        destination_dir = os.path.join(_state_dir(), "support-bundles", timestamp)
    else:
        destination_dir = os.path.abspath(destination_dir)
    os.makedirs(destination_dir, exist_ok=True)

    files = {}
    health_path = os.path.join(destination_dir, "health_report.txt")
    with open(health_path, "w", encoding="utf-8") as file_handle:
        file_handle.write(_build_headless_health_report())
    files["health_report"] = health_path

    state_summary_path = os.path.join(destination_dir, "state_summary.json")
    _atomic_write_json(state_summary_path, _collect_state_summary_data(), sort_keys=True)
    files["state_summary"] = state_summary_path

    state_summary_text_path = os.path.join(destination_dir, "state_summary.txt")
    with open(state_summary_text_path, "w", encoding="utf-8") as file_handle:
        file_handle.write(_build_state_summary_report())
    files["state_summary_text"] = state_summary_text_path

    session_report_path = os.path.join(destination_dir, "session_report.json")
    _atomic_write_json(
        session_report_path,
        _build_session_report_payload(
            profile_data or {},
            activity_history or [],
            run_reports or [],
            state_files
            or {
                "profiles": _state_file_location(PROFILE_FILE_NAME),
                "workspace": _state_file_location(WORKSPACE_FILE_NAME),
            },
        ),
        sort_keys=True,
    )
    files["session_report"] = session_report_path

    backup_result = _backup_state_files(os.path.join(destination_dir, "state_backup"))
    manifest_path = os.path.join(destination_dir, "manifest.json")
    result = {
        "app_version": APP_VERSION,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "bundle_dir": destination_dir,
        "files": files,
        "backup": backup_result,
        "privacy_note": "Contains AutoClicker health, session, state summary, and known app-state files only.",
    }
    result["manifest_path"] = manifest_path
    _atomic_write_json(manifest_path, result, sort_keys=True)
    return result


def _validate_recording_file(file_path):
    points = _normalize_recording_points(_load_json_file(file_path), strict=True)
    return {
        "valid": True,
        "type": "recording",
        "path": file_path,
        "points": len(points),
    }


def _validate_sequence_file(file_path, click_types=None):
    steps = _normalize_sequence_steps(_load_json_file(file_path), click_types=click_types)
    total_wait = sum(step[3] for step in steps)
    return {
        "valid": True,
        "type": "sequence",
        "path": file_path,
        "steps": len(steps),
        "total_wait_seconds": round(total_wait, 3),
    }


def _validate_profile_data(profile_name, profile_data, click_types=None):
    click_types = click_types or DEFAULT_CLICK_TYPES
    enum_fields = dict(PROFILE_ENUM_FIELDS)
    enum_fields["click_mode"] = set(click_types)

    result = {
        "name": str(profile_name),
        "valid": True,
        "errors": [],
        "warnings": [],
        "unknown_fields": [],
    }

    if not isinstance(profile_name, str) or not profile_name.strip():
        result["errors"].append("profile name must be a non-empty string")
    if not isinstance(profile_data, dict):
        result["errors"].append("profile data must be a JSON object")
        result["valid"] = False
        return result

    unknown_fields = sorted(str(field_name) for field_name in set(profile_data) - PROFILE_FIELDS)
    result["unknown_fields"] = unknown_fields
    if unknown_fields:
        result["warnings"].append("unknown fields: " + ", ".join(unknown_fields))

    for field_name in PROFILE_INT_FIELDS & set(profile_data):
        try:
            value = int(profile_data[field_name])
        except Exception:
            result["errors"].append(f"{field_name} must be an integer")
            continue
        if field_name in {"jitter_x", "jitter_y", "max_actions", "micro_pause_every", "repeat_count"} and value < 0:
            result["errors"].append(f"{field_name} must be zero or greater")
        if field_name == "repeat_count" and value < 1:
            result["errors"].append("repeat_count must be at least 1")

    for field_name in PROFILE_FLOAT_FIELDS & set(profile_data):
        try:
            value = float(profile_data[field_name])
        except Exception:
            result["errors"].append(f"{field_name} must be a number")
            continue
        if field_name in {
            "delay",
            "delay_variance",
            "countdown",
            "runtime_limit",
            "micro_pause_duration",
        } and value < 0:
            result["errors"].append(f"{field_name} must be zero or greater")
        if field_name == "window_opacity" and not 0.2 <= value <= 1.0:
            result["warnings"].append("window_opacity is outside the normal 0.2-1.0 range")
        if field_name == "ui_scale" and not 0.5 <= value <= 2.0:
            result["warnings"].append("ui_scale is outside the normal 0.5-2.0 range")

    for field_name in PROFILE_BOOL_FIELDS & set(profile_data):
        if not isinstance(profile_data[field_name], bool):
            result["warnings"].append(f"{field_name} will be interpreted as {'enabled' if bool(profile_data[field_name]) else 'disabled'}")

    for field_name, allowed_values in enum_fields.items():
        if field_name in profile_data and profile_data[field_name] not in allowed_values:
            result["errors"].append(
                f"{field_name} must be one of: {', '.join(sorted(allowed_values))}"
            )

    result["valid"] = not result["errors"]
    return result


def _preview_profile_import(imported_profiles, existing_profiles=None, click_types=None):
    if not isinstance(imported_profiles, dict):
        raise ValueError("Profile files must contain a JSON object of profiles.")

    existing_profiles = existing_profiles or {}
    valid_profiles = {}
    invalid_profiles = []
    warnings_by_profile = {}
    overwrites = []
    new_profiles = []

    for profile_name, profile_data in imported_profiles.items():
        validation = _validate_profile_data(profile_name, profile_data, click_types=click_types)
        if validation["valid"]:
            valid_profiles[profile_name] = profile_data
            if profile_name in existing_profiles:
                overwrites.append(profile_name)
            else:
                new_profiles.append(profile_name)
            if validation["warnings"]:
                warnings_by_profile[profile_name] = validation["warnings"]
        else:
            invalid_profiles.append(validation)

    return {
        "total_entries": len(imported_profiles),
        "valid_count": len(valid_profiles),
        "invalid_count": len(invalid_profiles),
        "overwrite_count": len(overwrites),
        "new_count": len(new_profiles),
        "valid_profile_names": sorted(valid_profiles),
        "invalid_profiles": invalid_profiles,
        "warnings_by_profile": warnings_by_profile,
        "overwrites": sorted(overwrites),
        "new_profiles": sorted(new_profiles),
        "valid_profiles": valid_profiles,
    }


def _validate_profiles_file(file_path, existing_profiles=None, click_types=None):
    preview = _preview_profile_import(
        _load_json_file(file_path),
        existing_profiles=existing_profiles,
        click_types=click_types,
    )
    preview["valid"] = preview["invalid_count"] == 0 and preview["valid_count"] > 0
    preview["path"] = file_path
    return preview


def _argument_value(arguments, flag):
    if flag not in arguments:
        return None
    index = arguments.index(flag)
    if index + 1 >= len(arguments) or arguments[index + 1].startswith("--"):
        return None
    return arguments[index + 1]


def _show_dependency_error(feature_name, packages, parent=None):
    install_hint = "pip install " + " ".join(packages)
    details = [f"{package}: {IMPORT_ERRORS[package]}" for package in packages if package in IMPORT_ERRORS]
    message = (
        f"{feature_name} requires the following package(s): {', '.join(packages)}.\n\n"
        f"Install them with:\n{install_hint}"
    )
    if details:
        message += "\n\nImport details:\n" + "\n".join(details)

    try:
        if parent is not None:
            messagebox.showerror("Missing dependency", message, parent=parent)
        else:
            messagebox.showerror("Missing dependency", message)
    except Exception:
        print(message, file=sys.stderr)


def _ensure_dependencies(feature_name, packages, parent=None):
    missing_packages = [package for package in packages if package in IMPORT_ERRORS]
    if missing_packages:
        _show_dependency_error(feature_name, missing_packages, parent=parent)
        return False
    return True


def _create_scrollable_shell(window, bg, min_width=700, padx=18, pady=18):
    host = tk.Frame(window, bg=bg)
    host.pack(fill="both", expand=True)
    host.columnconfigure(0, weight=1)
    host.rowconfigure(0, weight=1)

    canvas = tk.Canvas(host, bg=bg, highlightthickness=0, bd=0)
    canvas.grid(row=0, column=0, sticky="nsew")

    v_scroll = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
    v_scroll.grid(row=0, column=1, sticky="ns")
    h_scroll = ttk.Scrollbar(host, orient="horizontal", command=canvas.xview)
    h_scroll.grid(row=1, column=0, sticky="ew")
    canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    shell = tk.Frame(canvas, bg=bg, padx=padx, pady=pady)
    shell_window = canvas.create_window((0, 0), window=shell, anchor="nw")

    def update_scroll_region(_event=None):
        if not canvas.winfo_exists():
            return
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)

    def fit_shell_width(event=None):
        if not canvas.winfo_exists():
            return
        available_width = canvas.winfo_width() if event is None else event.width
        canvas.itemconfigure(shell_window, width=max(available_width - 2, min_width))
        update_scroll_region()

    shell.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", fit_shell_width)
    window.after_idle(fit_shell_width)
    return shell, canvas

def Photo_Clicker():
    """Public entry point — opens the Photo Clicker window."""

    if not _ensure_dependencies("Photo Clicker", ["pyautogui", "keyboard"]):
        return

    owner = tk._default_root
    win = tk.Toplevel(owner) if owner else tk.Tk()
    win.title("Photo Clicker")
    win.geometry("680x620+280+100")
    win.minsize(680, 620)
    win.attributes("-topmost", True)
    win.resizable(True, True)
    win.configure(bg=_BG)
    try:
        win.iconbitmap(_resource_path("favicon.ico"))
    except Exception:
        pass

    # ── state ────────────────────────────────────────────────────────────
    state = {
        "thread": None,
        "stop_event": threading.Event(),
        "image_path": None,
        "thumbnail": None,
    }
    ui_queue = queue.Queue()

    # ── variables ────────────────────────────────────────────────────────
    filepath_var   = tk.StringVar(value="No image selected")
    confidence_var = tk.StringVar(value="0.8")
    mode_var       = tk.StringVar(value="Click Once")
    burst_var      = tk.StringVar(value="5")
    interval_var   = tk.StringVar(value="1.00")
    button_var     = tk.StringVar(value="Left Click")
    hotkey_var     = tk.StringVar(value="esc")
    grayscale_var  = tk.BooleanVar(value=False)
    region_var     = tk.StringVar(value="Full Screen")
    rx1_var        = tk.StringVar(value="0")
    ry1_var        = tk.StringVar(value="0")
    rx2_var        = tk.StringVar(value="1920")
    ry2_var        = tk.StringVar(value="1080")
    status_var     = tk.StringVar(value="Select an image to locate on screen.")
    stats_var      = tk.StringVar(value="No scans yet.")

    try:
        sw, sh = pyautogui.size()
        rx2_var.set(str(sw))
        ry2_var.set(str(sh))
    except Exception:
        pass

    # ── helpers ──────────────────────────────────────────────────────────
    def _set_status(msg):
        if threading.current_thread() is threading.main_thread():
            status_var.set(msg)
        else:
            ui_queue.put(("status", msg))

    def _set_stats(msg):
        if threading.current_thread() is threading.main_thread():
            stats_var.set(msg)
        else:
            ui_queue.put(("stats", msg))

    def _set_controls_running(running):
        start_btn.configure(state=DISABLED if running else NORMAL)
        stop_btn.configure(state=NORMAL if running else DISABLED)

    def _pump_queue():
        try:
            while True:
                action, payload = ui_queue.get_nowait()
                if action == "status":
                    status_var.set(payload)
                elif action == "stats":
                    stats_var.set(payload)
                elif action == "finish":
                    state["thread"] = None
                    _set_controls_running(False)
        except queue.Empty:
            pass
        try:
            if win.winfo_exists():
                win.after(100, _pump_queue)
        except tk.TclError:
            pass

    def _stop_check():
        if state["stop_event"].is_set():
            return True
        if keyboard and hotkey_var.get().strip():
            try:
                if keyboard.is_pressed(hotkey_var.get().strip()):
                    state["stop_event"].set()
                    _set_status(f"Stop hotkey '{hotkey_var.get().strip()}' pressed.")
                    return True
            except Exception:
                pass
        return False

    # ── commands ─────────────────────────────────────────────────────────
    def pick_image():
        path = filedialog.askopenfilename(
            title="Select reference image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"),
                ("All files", "*.*"),
            ],
            parent=win,
        )
        if not path:
            return
        state["image_path"] = path
        filepath_var.set(os.path.basename(path))
        _set_status(f"Loaded: {os.path.basename(path)}")

        # thumbnail preview
        if Image and ImageTk:
            try:
                img = Image.open(path)
                img.thumbnail((160, 120), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                state["thumbnail"] = photo  # prevent GC
                thumb_label.configure(image=photo, text="")
            except Exception:
                thumb_label.configure(image="", text="(preview unavailable)")
        else:
            thumb_label.configure(image="", text="(Pillow not installed)")

    def _worker(image_path, conf, mode, burst_count, interval_sec,
                btn, clicks, use_grayscale, region):
        try:
            total_found = 0
            total_clicked = 0
            started = time.perf_counter()

            iterations = 0
            while not _stop_check():
                iterations += 1

                try:
                    loc = pyautogui.locateOnScreen(
                        image_path,
                        confidence=conf,
                        grayscale=use_grayscale,
                        region=region,
                    )
                except pyautogui.ImageNotFoundException:
                    loc = None
                except Exception as exc:
                    _set_status(f"Scan error: {exc}")
                    loc = None

                elapsed = time.perf_counter() - started

                if loc is not None:
                    total_found += 1
                    cx, cy = pyautogui.center(loc)
                    pyautogui.click(x=cx, y=cy, button=btn, clicks=clicks,
                                    interval=0.02 if clicks > 1 else 0.0)
                    total_clicked += 1
                    _set_status(f"Clicked image centre at ({cx}, {cy}).")
                    _set_stats(
                        f"Scan #{iterations} | found {total_found}x "
                        f"| clicked {total_clicked}x | {elapsed:.2f}s elapsed"
                    )
                else:
                    _set_status(f"Image not found on scan #{iterations}.")
                    _set_stats(
                        f"Scan #{iterations} | found {total_found}x "
                        f"| clicked {total_clicked}x | {elapsed:.2f}s elapsed"
                    )

                # exit conditions
                if mode == "Click Once":
                    break
                elif mode == "Burst Count":
                    if total_clicked >= burst_count:
                        _set_status(
                            f"Burst complete: {total_clicked} click(s) in "
                            f"{elapsed:.2f}s."
                        )
                        break
                # continuous watch — loop again after interval
                if not _stop_check() and mode != "Click Once":
                    state["stop_event"].wait(interval_sec)

        except Exception as exc:
            _set_status(f"Worker error: {exc}")
        finally:
            ui_queue.put(("finish", None))

    def start_scan():
        if state["thread"] and state["thread"].is_alive():
            _set_status("A scan is already running.")
            return
        if not state["image_path"]:
            messagebox.showerror("No image", "Select a reference image first.",
                                 parent=win)
            return

        try:
            conf = float(confidence_var.get())
            if not 0 < conf <= 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid confidence",
                                 "Confidence must be between 0 and 1.",
                                 parent=win)
            return

        click_map = {
            "Left Click": ("left", 1),
            "Right Click": ("right", 1),
            "Middle Click": ("middle", 1),
            "Double Left Click": ("left", 2),
            "Double Right Click": ("right", 2),
        }
        btn_info = click_map.get(button_var.get(), ("left", 1))

        mode = mode_var.get()
        try:
            burst_count = int(burst_var.get()) if mode == "Burst Count" else 1
        except ValueError:
            burst_count = 1

        try:
            interval_sec = float(interval_var.get())
        except ValueError:
            interval_sec = 1.0

        use_grayscale = grayscale_var.get()

        region = None
        if region_var.get() == "Custom Region":
            try:
                rx1 = int(rx1_var.get())
                ry1 = int(ry1_var.get())
                rx2 = int(rx2_var.get())
                ry2 = int(ry2_var.get())
                region = (min(rx1, rx2), min(ry1, ry2),
                          abs(rx2 - rx1), abs(ry2 - ry1))
                if region[2] == 0 or region[3] == 0:
                    raise ValueError("Zero-size region")
            except Exception as exc:
                messagebox.showerror("Invalid region", str(exc), parent=win)
                return

        state["stop_event"].clear()
        _set_controls_running(True)
        _set_status("Scanning for image…")

        state["thread"] = threading.Thread(
            target=_worker,
            args=(state["image_path"], conf, mode, burst_count, interval_sec,
                  btn_info[0], btn_info[1], use_grayscale, region),
            daemon=True,
        )
        state["thread"].start()

    def stop_scan():
        if state["thread"] and state["thread"].is_alive():
            state["stop_event"].set()
            _set_status("Stop requested.")

    def close_window():
        state["stop_event"].set()
        win.destroy()

    def _toggle_region(*_):
        is_custom = region_var.get() == "Custom Region"
        for widget in (rx1_entry, ry1_entry, rx2_entry, ry2_entry):
            widget.configure(state=NORMAL if is_custom else DISABLED)

    def _toggle_burst(*_):
        burst_entry.configure(
            state=NORMAL if mode_var.get() == "Burst Count" else DISABLED
        )

    # ── styles ───────────────────────────────────────────────────────────
    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("PC.Accent.TButton", background=_ACCENT,
                    foreground="white", padding=(14, 8),
                    font=("Segoe UI", 10, "bold"))
    style.map("PC.Accent.TButton",
              background=[("active", "#115e59"), ("disabled", "#94a3b8")])
    style.configure("PC.Danger.TButton", background=_DANGER,
                    foreground="white", padding=(12, 8),
                    font=("Segoe UI", 10, "bold"))
    style.map("PC.Danger.TButton",
              background=[("active", "#991b1b"), ("disabled", "#94a3b8")])
    style.configure("PC.Secondary.TButton", background="#e2e8f0",
                    foreground="#0f172a", padding=(12, 7),
                    font=("Segoe UI", 10))
    style.map("PC.Secondary.TButton", background=[("active", "#cbd5e1")])

    # ── layout ───────────────────────────────────────────────────────────
    shell = tk.Frame(win, bg=_BG, padx=18, pady=18)
    shell.pack(fill="both", expand=True)
    shell.columnconfigure(0, weight=1)

    # hero header
    hero = tk.Frame(shell, bg=_HERO_BG, padx=20, pady=14)
    hero.grid(row=0, column=0, sticky="ew")
    tk.Label(hero, text="Photo Clicker", bg=_HERO_BG, fg=_HERO_FG,
             font=("Segoe UI", 16, "bold")).pack(anchor="w")
    tk.Label(hero, text="Locate a reference image on screen and click on it "
             "automatically.", bg=_HERO_BG, fg=_HERO_SUB,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

    # main card
    card = tk.Frame(shell, bg=_CARD_BG, padx=16, pady=16,
                    highlightbackground=_BORDER, highlightthickness=1)
    card.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
    card.columnconfigure(1, weight=1)
    card.columnconfigure(3, weight=1)
    shell.rowconfigure(1, weight=1)

    # row 0 — image picker
    tk.Label(card, text="Reference image", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky=W,
                                                  pady=(0, 6))
    tk.Label(card, textvariable=filepath_var, bg=_CARD_BG, fg="#475569",
             font=("Segoe UI", 10)).grid(row=0, column=1, sticky=W,
                                          pady=(0, 6))
    ttk.Button(card, text="Browse…", style="PC.Secondary.TButton",
               command=pick_image).grid(row=0, column=2, columnspan=2,
                                        sticky="e", pady=(0, 6))

    # row 1 — thumbnail preview
    tk.Label(card, text="Preview", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="nw",
                                                  pady=(0, 10))
    thumb_label = tk.Label(card, text="(no image)", bg="#e2e8f0", fg="#64748b",
                           width=22, height=7, relief="solid", bd=1,
                           font=("Segoe UI", 9))
    thumb_label.grid(row=1, column=1, sticky=W, pady=(0, 10))

    # row 2 — confidence + click type
    tk.Label(card, text="Confidence (0-1)", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky=W,
                                                  pady=(0, 6))
    ttk.Entry(card, textvariable=confidence_var, width=12).grid(
        row=2, column=1, sticky=W, pady=(0, 6))
    tk.Label(card, text="Click type", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=2, column=2, sticky=W,
                                                  padx=(14, 0), pady=(0, 6))
    ttk.Combobox(card, textvariable=button_var, state="readonly", width=18,
                 values=("Left Click", "Right Click", "Middle Click",
                         "Double Left Click", "Double Right Click")).grid(
        row=2, column=3, sticky=W, pady=(0, 6))

    # row 3 — mode + burst count
    tk.Label(card, text="Mode", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky=W,
                                                  pady=(0, 6))
    mode_combo = ttk.Combobox(card, textvariable=mode_var, state="readonly",
                              width=18,
                              values=("Click Once", "Burst Count",
                                      "Continuous Watch"))
    mode_combo.grid(row=3, column=1, sticky=W, pady=(0, 6))
    tk.Label(card, text="Burst count", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=3, column=2, sticky=W,
                                                  padx=(14, 0), pady=(0, 6))
    burst_entry = ttk.Entry(card, textvariable=burst_var, width=12,
                            state=DISABLED)
    burst_entry.grid(row=3, column=3, sticky=W, pady=(0, 6))

    # row 4 — scan interval + stop hotkey
    tk.Label(card, text="Scan interval (sec)", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky=W,
                                                  pady=(0, 6))
    ttk.Entry(card, textvariable=interval_var, width=12).grid(
        row=4, column=1, sticky=W, pady=(0, 6))
    tk.Label(card, text="Stop hotkey", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=4, column=2, sticky=W,
                                                  padx=(14, 0), pady=(0, 6))
    ttk.Entry(card, textvariable=hotkey_var, width=12).grid(
        row=4, column=3, sticky=W, pady=(0, 6))

    # row 5 — grayscale + region selector
    ttk.Checkbutton(card, text="Grayscale matching (faster, less precise)",
                    variable=grayscale_var).grid(
        row=5, column=0, columnspan=2, sticky=W, pady=(0, 6))
    tk.Label(card, text="Region", bg=_CARD_BG, fg=_LABEL_FG,
             font=("Segoe UI", 10, "bold")).grid(row=5, column=2, sticky=W,
                                                  padx=(14, 0), pady=(0, 6))
    region_combo = ttk.Combobox(card, textvariable=region_var, state="readonly",
                                width=18,
                                values=("Full Screen", "Custom Region"))
    region_combo.grid(row=5, column=3, sticky=W, pady=(0, 6))

    # row 6 — custom region fields
    region_frame = ttk.LabelFrame(card, text="Custom region", padding=8)
    region_frame.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(4, 8))
    ttk.Label(region_frame, text="X1").grid(row=0, column=0, sticky=W)
    rx1_entry = ttk.Entry(region_frame, textvariable=rx1_var, width=8,
                          state=DISABLED)
    rx1_entry.grid(row=0, column=1, padx=(0, 10))
    ttk.Label(region_frame, text="Y1").grid(row=0, column=2, sticky=W)
    ry1_entry = ttk.Entry(region_frame, textvariable=ry1_var, width=8,
                          state=DISABLED)
    ry1_entry.grid(row=0, column=3, padx=(0, 10))
    ttk.Label(region_frame, text="X2").grid(row=0, column=4, sticky=W)
    rx2_entry = ttk.Entry(region_frame, textvariable=rx2_var, width=8,
                          state=DISABLED)
    rx2_entry.grid(row=0, column=5, padx=(0, 10))
    ttk.Label(region_frame, text="Y2").grid(row=0, column=6, sticky=W)
    ry2_entry = ttk.Entry(region_frame, textvariable=ry2_var, width=8,
                          state=DISABLED)
    ry2_entry.grid(row=0, column=7)

    # row 7 — action buttons
    btn_row = tk.Frame(card, bg=_CARD_BG)
    btn_row.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(6, 4))
    start_btn = ttk.Button(btn_row, text="Start Scan", style="PC.Accent.TButton",
                           command=start_scan)
    start_btn.grid(row=0, column=0, padx=(0, 8))
    stop_btn = ttk.Button(btn_row, text="Stop", style="PC.Danger.TButton",
                          command=stop_scan, state=DISABLED)
    stop_btn.grid(row=0, column=1)

    # status strip
    status_frame = tk.Frame(shell, bg=_STATUS_BG, padx=16, pady=10)
    status_frame.grid(row=2, column=0, sticky="ew", pady=(14, 0))
    tk.Label(status_frame, text="Status", bg=_STATUS_BG, fg=_HERO_FG,
             font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky=W)
    tk.Label(status_frame, textvariable=status_var, bg=_STATUS_BG,
             fg=_STATUS_FG, font=("Segoe UI", 10), wraplength=600,
             justify=LEFT).grid(row=1, column=0, sticky=W, pady=(4, 0))
    tk.Label(status_frame, textvariable=stats_var, bg=_STATUS_BG,
             fg=_STATUS_FG, font=("Segoe UI", 9), wraplength=600,
             justify=LEFT).grid(row=2, column=0, sticky=W, pady=(4, 0))

    # bindings
    mode_combo.bind("<<ComboboxSelected>>", _toggle_burst)
    region_combo.bind("<<ComboboxSelected>>", _toggle_region)

    _pump_queue()
    win.protocol("WM_DELETE_WINDOW", close_window)
    if owner is None:
        win.mainloop()


# allow standalone execution


try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from pprint import pprint
except:
    pass

try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*", category=UserWarning)
        import win10toast #This module only works on windows
except:
    pass

try:
    from PIL import ImageGrab
    from colormap import rgb2hex
    from win32api import GetSystemMetrics
except:
    pass

################################################################################
#     /\  | |  | |__   __/ __ \   / ____| |    |_   _/ ____| |/ /  ____|  __ \ #
#    /  \ | |  | |  | | | |  | | | |    | |      | || |    | ' /| |__  | |__) |#
#   / /\ \| |  | |  | | | |  | | | |    | |      | || |    |  < |  __| |  _  / #
#  / ____ \ |__| |  | | | |__| | | |____| |____ _| || |____| . \| |____| | \ \ #
# /_/    \_\____/   |_|  \____/   \_____|______|_____\_____|_|\_\______|_|  \_\#
################################################################################

def Colour_Clicker():
    """Advanced Colour Clicker with NumPy performance and Magnified Pipette."""
    if not _ensure_dependencies("Advanced Colour Clicker", ["pyautogui", "keyboard"], parent=tk._default_root):
        return
    if ImageGrab is None:
        _show_dependency_error("Advanced Colour Clicker", ["Pillow"], parent=tk._default_root)
        return

    _BG        = "#edf0f7"
    _CARD_BG   = "#f8fafc"
    _BORDER    = "#bfd0e5"
    _HERO_BG   = "#1e293b"
    _HERO_FG   = "#f8fafc"
    _HERO_SUB  = "#94a3b8"
    _LABEL_FG  = "#0f172a"
    _ACCENT    = "#0f766e"
    _DANGER    = "#b91c1c"

    owner = tk._default_root
    master = tk.Toplevel(owner) if owner else tk.Tk()
    master.title("Advanced Colour Clicker")
    master.geometry("720x780+300+100")
    master.minsize(700, 700)
    master.attributes("-topmost", True)
    master.configure(bg=_BG)
    try: master.iconbitmap(_resource_path("favicon.ico"))
    except: pass

    try:
        import numpy as np
        HAS_NUMPY = True
    except ImportError:
        HAS_NUMPY = False

    try:
        from PIL import Image, ImageTk
        HAS_PIL_UI = True
    except ImportError:
        HAS_PIL_UI = False

    try: screen_width, screen_height = pyautogui.size()
    except: screen_width, screen_height = 1920, 1080

    state = {"thread": None, "stop_event": threading.Event(), "is_sampling": False, "loupe_win": None, "loupe_canvas": None}
    ui_queue = queue.Queue()

    colour_var = tk.StringVar(value="#FFFFFF")
    tolerance_var = tk.StringVar(value="8")
    x_start_var = tk.StringVar(value="0")
    y_start_var = tk.StringVar(value="0")
    x_end_var = tk.StringVar(value=str(screen_width))
    y_end_var = tk.StringVar(value=str(screen_height))
    scan_step_var = tk.StringVar(value="2")
    interval_var = tk.StringVar(value="0.50")
    button_var = tk.StringVar(value="Left Click")
    mode_var = tk.StringVar(value="First Match")
    hotkey_var = tk.StringVar(value="esc")
    status_var = tk.StringVar(value="Ready. Sample a colour or select an area.")
    stats_var = tk.StringVar(value="No scans yet.")

    def set_status(msg): ui_queue.put(("status", msg))
    def set_stats(msg): ui_queue.put(("stats", msg))

    def pump_ui_queue():
        try:
            while True:
                t, d = ui_queue.get_nowait()
                if t == "status": status_var.set(d)
                elif t == "stats": stats_var.set(d)
                elif t == "finish":
                    state["thread"] = None
                    scan_btn.configure(state=NORMAL)
                    watch_btn.configure(state=NORMAL)
                    stop_btn.configure(state=DISABLED)
        except queue.Empty: pass
        master.after(100, pump_ui_queue)

    def select_area():
        overlay = tk.Toplevel(master)
        overlay.attributes("-alpha", 0.3)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="black")
        overlay.focus_force()
        canvas = tk.Canvas(overlay, cursor="cross", bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        sel = {"x1": 0, "y1": 0, "rect": None}
        def on_down(e):
            sel["x1"], sel["y1"] = e.x, e.y
            sel["rect" ] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="white", width=2)
        def on_move(e):
            if sel["rect"]: canvas.coords(sel["rect"], sel["x1"], sel["y1"], e.x, e.y)
        def on_up(e):
            x1, y1, x2, y2 = sel["x1"], sel["y1"], e.x, e.y
            x_start_var.set(str(min(x1, x2))); y_start_var.set(str(min(y1, y2)))
            x_end_var.set(str(max(x1, x2))); y_end_var.set(str(max(y1, y2)))
            overlay.destroy()
            set_status(f"Region set to ({x_start_var.get()}, {y_start_var.get()}) to ({x_end_var.get()}, {y_end_var.get()})")
        overlay.bind("<ButtonPress-1>", on_down)
        overlay.bind("<B1-Motion>", on_move)
        overlay.bind("<ButtonRelease-1>", on_up)
        overlay.bind("<Escape>", lambda _: overlay.destroy())

    def update_loupe():
        if not state["is_sampling"]: return
        try:
            x, y = pyautogui.position()
            state["loupe_win"].geometry(f"+{(x + 20)}+{(y + 20)}")
            if HAS_PIL_UI:
                img = ImageGrab.grab(bbox=(x-10, y-10, x+11, y+11)).convert("RGB")
                img_zoom = img.resize((147, 147), Image.NEAREST)
                photo = ImageTk.PhotoImage(img_zoom)
                state["loupe_canvas"].delete("all")
                state["loupe_canvas"].create_image(0, 0, anchor="nw", image=photo)
                state["loupe_canvas"].image = photo
                state["loupe_canvas"].create_line(73, 0, 73, 147, fill="red")
                state["loupe_canvas"].create_line(0, 73, 147, 73, fill="red")
                r, g, b = img.getpixel((10, 10))
                state["loupe_win"].title(f"#{r:02X}{g:02X}{b:02X}")
        except: pass
        master.after(30, update_loupe)

    def start_sampling():
        if state["is_sampling"]: return
        state["is_sampling"] = True
        set_status("Sample colour: Click target pixel. ESC to cancel.")
        master.config(cursor="cross")
        lwin = tk.Toplevel(master)
        lwin.overrideredirect(True)
        lwin.attributes("-topmost", True)
        lwin.geometry("150x150")
        lwin.configure(bg="black", highlightbackground="white", highlightthickness=2)
        lcanv = tk.Canvas(lwin, width=147, height=147, bg="black", highlightthickness=0)
        lcanv.pack()
        state["loupe_win"] = lwin
        state["loupe_canvas"] = lcanv
        update_loupe()
        def perform_sample(e=None):
            x, y = pyautogui.position()
            img = ImageGrab.grab(bbox=(x, y, x+1, y+1)).convert('RGB')
            r, g, b = img.getpixel((0, 0))
            colour_var.set("#{:02X}{:02X}{:02X}".format(r, g, b))
            update_preview(); cancel_sampling()
        def cancel_sampling(e=None):
            state["is_sampling"] = False; master.config(cursor="")
            if state["loupe_win"]: state["loupe_win"].destroy()
            master.unbind("<Button-1>"); 
            try: keyboard.unhook_all_hotkeys()
            except: pass
        master.bind("<Button-1>", perform_sample)
        keyboard.add_hotkey("esc", cancel_sampling)

    def update_preview(*_):
        try:
            col = colour_var.get(); preview_box.configure(bg=col)
        except: pass

    def worker(target_hex, tolerance, bbox, step, mode, is_watcher, interval, btn, clicks, stop_hk):
        try:
            target_rgb = tuple(int(target_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            iterations = 0; found_total = 0
            while not state["stop_event"].is_set():
                iterations += 1
                if stop_hk and keyboard.is_pressed(stop_hk): break
                img = ImageGrab.grab(bbox=bbox).convert("RGB")
                found_points = []
                if HAS_NUMPY:
                    arr = np.array(img)
                    diff = np.abs(arr - target_rgb)
                    match_mask = np.all(diff <= tolerance, axis=-1)
                    match_mask = match_mask[::step, ::step]
                    y_coords, x_coords = np.where(match_mask)
                    for y, x in zip(y_coords, x_coords): found_points.append((bbox[0] + x*step, bbox[1] + y*step))
                else:
                    for y in range(0, img.height, step):
                        for x in range(0, img.width, step):
                            r, g, b = img.getpixel((x, y))
                            if all(abs(c-t) <= tolerance for c, t in zip((r, g, b), target_rgb)):
                                found_points.append((bbox[0]+x, bbox[1]+y))
                                if mode == "First Match": break
                        if mode == "First Match" and found_points: break
                if found_points:
                    if mode == "First Match": pyautogui.click(found_points[0][0], found_points[0][1], button=btn, clicks=clicks); found_total += 1
                    else:
                        for px, py in found_points:
                            if state["stop_event"].is_set(): break
                            pyautogui.click(px, py, button=btn, clicks=clicks); found_total += 1
                    set_status(f"Found {len(found_points)} match(es).")
                else: set_status(f"No match in scan #{iterations}.")
                set_stats(f"Scans: {iterations} | Clicks: {found_total}")
                if not is_watcher: break
                state["stop_event"].wait(interval)
        except Exception as e: set_status(f"Error: {e}")
        finally: ui_queue.put(("finish", None))

    def start_worker(is_watcher):
        try:
            col, tol, step = colour_var.get(), int(tolerance_var.get()), int(scan_step_var.get())
            bbox = (int(x_start_var.get()), int(y_start_var.get()), int(x_end_var.get()), int(y_end_var.get()))
            interval = float(interval_var.get()); btn = "left" if "Left" in button_var.get() else "right"
            clicks = 2 if "Double" in button_var.get() else 1; stop_hk = hotkey_var.get()
            state["stop_event"].clear(); scan_btn.configure(state=DISABLED); watch_btn.configure(state=DISABLED); stop_btn.configure(state=NORMAL)
            state["thread"] = threading.Thread(target=worker, args=(col, tol, bbox, step, mode_var.get(), is_watcher, interval, btn, clicks, stop_hk), daemon=True)
            state["thread"].start()
        except Exception as e: messagebox.showerror("Error", str(e))

    shell = tk.Frame(master, bg=_BG, padx=20, pady=20); shell.pack(fill="both", expand=True)
    hero = tk.Frame(shell, bg=_HERO_BG, padx=20, pady=15); hero.pack(fill="x")
    tk.Label(hero, text="Advanced Colour Clicker", bg=_HERO_BG, fg=_HERO_FG, font=("Segoe UI", 16, "bold")).pack(anchor="w")
    tk.Label(hero, text="Scan screen regions for colours with NumPy speed.", bg=_HERO_BG, fg=_HERO_SUB, font=("Segoe UI", 9)).pack(anchor="w")
    card1 = tk.Frame(shell, bg=_CARD_BG, padx=15, pady=15, highlightbackground=_BORDER, highlightthickness=1); card1.pack(fill="x", pady=(15, 0))
    tk.Label(card1, text="Target Colour & Tolerance", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))
    trow = tk.Frame(card1, bg=_CARD_BG); trow.pack(fill="x")
    preview_box = tk.Frame(trow, width=40, height=40, relief="solid", bd=1); preview_box.pack(side="left", padx=(0, 10))
    ttk.Entry(trow, textvariable=colour_var, width=12).pack(side="left", padx=(0, 10))
    ttk.Button(trow, text="Pipette", command=start_sampling).pack(side="left", padx=(0, 10))
    tk.Label(trow, text="Tolerance:", bg=_CARD_BG).pack(side="left"); ttk.Entry(trow, textvariable=tolerance_var, width=8).pack(side="left", padx=(5, 0))
    card2 = tk.Frame(shell, bg=_CARD_BG, padx=15, pady=15, highlightbackground=_BORDER, highlightthickness=1); card2.pack(fill="x", pady=(15, 0))
    tk.Label(card2, text="Scan Region", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))
    rg = tk.Frame(card2, bg=_CARD_BG); rg.pack(fill="x")
    tk.Label(rg, text="X1", bg=_CARD_BG).grid(row=0, column=0, padx=2); ttk.Entry(rg, textvariable=x_start_var, width=7).grid(row=0, column=1)
    tk.Label(rg, text="Y1", bg=_CARD_BG).grid(row=0, column=2, padx=2); ttk.Entry(rg, textvariable=y_start_var, width=7).grid(row=0, column=3)
    tk.Label(rg, text="X2", bg=_CARD_BG).grid(row=0, column=4, padx=2); ttk.Entry(rg, textvariable=x_end_var, width=7).grid(row=0, column=5)
    tk.Label(rg, text="Y2", bg=_CARD_BG).grid(row=0, column=6, padx=2); ttk.Entry(rg, textvariable=y_end_var, width=7).grid(row=0, column=7)
    ttk.Button(rg, text="Select Area", command=select_area).grid(row=0, column=8, padx=10)
    card3 = tk.Frame(shell, bg=_CARD_BG, padx=15, pady=15, highlightbackground=_BORDER, highlightthickness=1); card3.pack(fill="x", pady=(15, 0))
    er = tk.Frame(card3, bg=_CARD_BG); er.pack(fill="x")
    tk.Label(er, text="Mode:", bg=_CARD_BG).pack(side="left"); ttk.Combobox(er, textvariable=mode_var, values=("First Match", "All Matches"), state="readonly", width=14).pack(side="left", padx=4)
    tk.Label(er, text="Step:", bg=_CARD_BG).pack(side="left", padx=(6, 0)); ttk.Entry(er, textvariable=scan_step_var, width=5).pack(side="left", padx=4)
    tk.Label(er, text="Btn:", bg=_CARD_BG).pack(side="left", padx=(6, 0)); ttk.Combobox(er, textvariable=button_var, values=("Left Click", "Right Click", "Double Left"), state="readonly", width=12).pack(side="left", padx=4)
    br = tk.Frame(shell, bg=_BG); br.pack(fill="x", pady=(20, 0))
    scan_btn = ttk.Button(br, text="Single Scan", command=lambda: start_worker(False)); scan_btn.pack(side="left", padx=(0, 10))
    watch_btn = ttk.Button(br, text="Watch Region", command=lambda: start_worker(True)); watch_btn.pack(side="left", padx=(0, 10))
    stop_btn = ttk.Button(br, text="Stop", state=DISABLED, command=lambda: state["stop_event"].set()); stop_btn.pack(side="left")
    ss = tk.Frame(shell, bg="#0f172a", padx=15, pady=10); ss.pack(fill="x", side="bottom")
    tk.Label(ss, textvariable=status_var, bg="#0f172a", fg="#f8fafc", font=("Segoe UI", 9)).pack(anchor="w")
    tk.Label(ss, textvariable=stats_var, bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 8)).pack(anchor="w")
    pump_ui_queue(); update_preview()
    master.protocol("WM_DELETE_WINDOW", lambda: (state["stop_event"].set(), master.destroy()))


def Photo_Clicker():
    """Public entry point for the upgraded Photo Clicker."""

    if not _ensure_dependencies("Photo Clicker", ["pyautogui", "keyboard"]):
        return

    _BG = "#edf0f7"
    _CARD_BG = "#f8fafc"
    _BORDER = "#bfd0e5"
    _HERO_BG = "#1e293b"
    _HERO_FG = "#f8fafc"
    _HERO_SUB = "#94a3b8"
    _LABEL_FG = "#0f172a"
    _ACCENT = "#0f766e"
    _DANGER = "#b91c1c"
    _STATUS_BG = "#0f172a"
    _STATUS_FG = "#cbd5e1"

    owner = tk._default_root
    win = tk.Toplevel(owner) if owner else tk.Tk()
    win.title("Photo Clicker")
    win.geometry("760x700+280+100")
    win.minsize(700, 620)
    win.attributes("-topmost", True)
    win.resizable(True, True)
    win.configure(bg=_BG)
    try:
        win.iconbitmap(_resource_path("favicon.ico"))
    except Exception:
        pass

    state = {
        "thread": None,
        "stop_event": threading.Event(),
        "image_path": None,
        "thumbnail": None,
    }
    ui_queue = queue.Queue()

    filepath_var = tk.StringVar(value="No image selected")
    confidence_var = tk.StringVar(value="0.80")
    mode_var = tk.StringVar(value="Click Once")
    burst_var = tk.StringVar(value="5")
    interval_var = tk.StringVar(value="1.00")
    button_var = tk.StringVar(value="Left Click")
    hotkey_var = tk.StringVar(value="esc")
    grayscale_var = tk.BooleanVar(value=False)
    region_var = tk.StringVar(value="Full Screen")
    preset_var = tk.StringVar(value="Balanced")
    focus_size_var = tk.StringVar(value="420")
    offset_x_var = tk.StringVar(value="0")
    offset_y_var = tk.StringVar(value="0")
    settle_delay_var = tk.StringVar(value="0.00")
    rx1_var = tk.StringVar(value="0")
    ry1_var = tk.StringVar(value="0")
    rx2_var = tk.StringVar(value="1920")
    ry2_var = tk.StringVar(value="1080")
    beep_var = tk.BooleanVar(value=False)
    status_var = tk.StringVar(value="Select an image to locate on screen.")
    stats_var = tk.StringVar(value="No scans yet.")
    region_summary_var = tk.StringVar(value="Full screen region ready.")

    try:
        screen_width, screen_height = pyautogui.size()
        rx2_var.set(str(screen_width))
        ry2_var.set(str(screen_height))
    except Exception:
        screen_width, screen_height = 1920, 1080

    def set_status(message):
        if threading.current_thread() is threading.main_thread():
            status_var.set(message)
        else:
            ui_queue.put(("status", message))

    def set_stats(message):
        if threading.current_thread() is threading.main_thread():
            stats_var.set(message)
        else:
            ui_queue.put(("stats", message))

    def set_controls_running(running):
        start_btn.configure(state=DISABLED if running else NORMAL)
        stop_btn.configure(state=NORMAL if running else DISABLED)

    def pump_queue():
        try:
            while True:
                action, payload = ui_queue.get_nowait()
                if action == "status":
                    status_var.set(payload)
                elif action == "stats":
                    stats_var.set(payload)
                elif action == "finish":
                    state["thread"] = None
                    set_controls_running(False)
        except queue.Empty:
            pass
        try:
            if win.winfo_exists():
                win.after(100, pump_queue)
        except tk.TclError:
            pass

    def stop_check():
        if state["stop_event"].is_set():
            return True
        stop_hotkey = hotkey_var.get().strip()
        if stop_hotkey and keyboard:
            try:
                if keyboard.is_pressed(stop_hotkey):
                    state["stop_event"].set()
                    set_status(f"Stop hotkey '{stop_hotkey}' pressed.")
                    return True
            except Exception:
                pass
        return False

    def update_region_summary(*_args):
        if region_var.get() != "Custom Region":
            region_summary_var.set("Full screen region ready.")
            return
        try:
            x1 = int(rx1_var.get())
            y1 = int(ry1_var.get())
            x2 = int(rx2_var.get())
            y2 = int(ry2_var.get())
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            if width == 0 or height == 0:
                raise ValueError
            region_summary_var.set(
                f"Custom region {width} x {height} at {min(x1, x2)}, {min(y1, y2)}."
            )
        except Exception:
            region_summary_var.set("Custom region pending valid coordinates.")

    def toggle_region(*_args):
        is_custom = region_var.get() == "Custom Region"
        for widget in (rx1_entry, ry1_entry, rx2_entry, ry2_entry):
            widget.configure(state=NORMAL if is_custom else DISABLED)
        update_region_summary()

    def toggle_burst(*_args):
        burst_entry.configure(state=NORMAL if mode_var.get() == "Burst Count" else DISABLED)

    def set_full_screen_region(set_mode=False):
        rx1_var.set("0")
        ry1_var.set("0")
        rx2_var.set(str(screen_width))
        ry2_var.set(str(screen_height))
        if set_mode:
            region_var.set("Full Screen")
            toggle_region()
        set_status("Region reset to the full screen.")

    def focus_region_near_cursor():
        try:
            focus_size = max(40, int(focus_size_var.get()))
        except ValueError:
            messagebox.showerror("Invalid focus size", "Focus size must be a whole number.", parent=win)
            return

        try:
            cursor_x, cursor_y = pyautogui.position()
        except Exception as exc:
            messagebox.showerror("Capture failed", f"Unable to read the cursor position.\n{exc}", parent=win)
            return

        half_size = focus_size // 2
        x1 = max(0, cursor_x - half_size)
        y1 = max(0, cursor_y - half_size)
        x2 = min(screen_width, cursor_x + half_size)
        y2 = min(screen_height, cursor_y + half_size)
        rx1_var.set(str(x1))
        ry1_var.set(str(y1))
        rx2_var.set(str(x2))
        ry2_var.set(str(y2))
        region_var.set("Custom Region")
        toggle_region()
        set_status(f"Focused the scan region around cursor {cursor_x}, {cursor_y}.")

    def open_image_folder():
        image_path = state["image_path"]
        if not image_path:
            messagebox.showinfo("Photo Clicker", "Choose an image first.", parent=win)
            return
        try:
            os.startfile(os.path.dirname(image_path))
        except Exception as exc:
            messagebox.showerror("Open folder failed", f"Unable to open the image folder.\n{exc}", parent=win)

    def apply_scan_preset(*_args):
        preset_name = preset_var.get()
        preset_map = {
            "Balanced": ("0.80", "1.00", False, "Click Once", "5"),
            "Precision Hunt": ("0.90", "1.20", False, "Click Once", "3"),
            "Fast Watch": ("0.72", "0.25", True, "Continuous Watch", "5"),
            "Burst Sweep": ("0.78", "0.40", True, "Burst Count", "8"),
        }
        confidence, interval, grayscale, mode_name, burst_total = preset_map.get(
            preset_name,
            preset_map["Balanced"],
        )
        confidence_var.set(confidence)
        interval_var.set(interval)
        grayscale_var.set(grayscale)
        mode_var.set(mode_name)
        burst_var.set(burst_total)
        toggle_burst()
        set_status(f"Preset '{preset_name}' applied.")

    def pick_image():
        path = filedialog.askopenfilename(
            title="Select reference image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"),
                ("All files", "*.*"),
            ],
            parent=win,
        )
        if not path:
            return

        state["image_path"] = path
        filepath_var.set(os.path.basename(path))
        set_status(f"Loaded reference image {os.path.basename(path)}.")

        if Image and ImageTk:
            try:
                image = Image.open(path)
                image.thumbnail((180, 130), Image.LANCZOS)
                preview = ImageTk.PhotoImage(image)
                state["thumbnail"] = preview
                thumb_label.configure(image=preview, text="")
            except Exception:
                thumb_label.configure(image="", text="(preview unavailable)")
        else:
            thumb_label.configure(image="", text="(Pillow not installed)")

    def parse_region():
        if region_var.get() != "Custom Region":
            return None
        try:
            x1 = int(rx1_var.get())
            y1 = int(ry1_var.get())
            x2 = int(rx2_var.get())
            y2 = int(ry2_var.get())
        except ValueError:
            raise ValueError("Region coordinates must be whole numbers.")

        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        if width == 0 or height == 0:
            raise ValueError("Custom region must have non-zero width and height.")
        return (left, top, width, height)

    def worker(
        image_path,
        confidence,
        mode_name,
        burst_count,
        interval_seconds,
        button_name,
        click_count,
        use_grayscale,
        region,
        offset_x,
        offset_y,
        settle_delay,
        should_beep,
    ):
        try:
            total_found = 0
            total_clicked = 0
            started_at = time.perf_counter()
            iteration = 0

            while not stop_check():
                iteration += 1
                try:
                    location = pyautogui.locateOnScreen(
                        image_path,
                        confidence=confidence,
                        grayscale=use_grayscale,
                        region=region,
                    )
                except Exception as exc:
                    if exc.__class__.__name__ == "ImageNotFoundException":
                        location = None
                    else:
                        set_status(f"Scan error: {exc}")
                        location = None

                elapsed = time.perf_counter() - started_at
                if location is None:
                    set_status(f"Image not found on scan #{iteration}.")
                    set_stats(
                        f"Scan #{iteration} | found {total_found}x | clicked {total_clicked}x | {elapsed:.2f}s elapsed"
                    )
                else:
                    total_found += 1
                    centre_x, centre_y = pyautogui.center(location)
                    click_x = int(centre_x + offset_x)
                    click_y = int(centre_y + offset_y)
                    if settle_delay > 0 and state["stop_event"].wait(settle_delay):
                        break
                    pyautogui.click(
                        x=click_x,
                        y=click_y,
                        button=button_name,
                        clicks=click_count,
                        interval=0.02 if click_count > 1 else 0.0,
                    )
                    total_clicked += 1
                    if should_beep and winsound:
                        try:
                            winsound.Beep(980, 60)
                        except Exception:
                            pass
                    set_status(
                        f"Match found at {centre_x}, {centre_y}. Clicked {click_x}, {click_y}."
                    )
                    set_stats(
                        f"Scan #{iteration} | found {total_found}x | clicked {total_clicked}x | {elapsed:.2f}s elapsed"
                    )

                if mode_name == "Click Once":
                    break
                if mode_name == "Burst Count" and total_clicked >= burst_count:
                    set_status(f"Burst complete after {total_clicked} click(s).")
                    break
                if mode_name != "Click Once" and not stop_check():
                    state["stop_event"].wait(interval_seconds)
        except Exception as exc:
            set_status(f"Worker error: {exc}")
        finally:
            ui_queue.put(("finish", None))

    def start_scan():
        if state["thread"] and state["thread"].is_alive():
            set_status("A scan is already running.")
            return
        if not state["image_path"]:
            messagebox.showerror("No image", "Select a reference image first.", parent=win)
            return

        try:
            confidence = float(confidence_var.get())
            if not 0 < confidence <= 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid confidence", "Confidence must be between 0 and 1.", parent=win)
            return

        try:
            interval_seconds = float(interval_var.get())
            if interval_seconds < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid interval", "Scan interval must be zero or greater.", parent=win)
            return

        try:
            settle_delay = float(settle_delay_var.get())
            if settle_delay < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid settle delay", "Settle delay must be zero or greater.", parent=win)
            return

        try:
            offset_x = int(offset_x_var.get())
            offset_y = int(offset_y_var.get())
        except ValueError:
            messagebox.showerror("Invalid click offset", "Offset values must be whole numbers.", parent=win)
            return

        mode_name = mode_var.get()
        try:
            burst_count = int(burst_var.get()) if mode_name == "Burst Count" else 1
            if burst_count < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid burst count", "Burst count must be at least 1.", parent=win)
            return

        click_map = {
            "Left Click": ("left", 1),
            "Right Click": ("right", 1),
            "Middle Click": ("middle", 1),
            "Double Left Click": ("left", 2),
            "Double Right Click": ("right", 2),
        }
        button_name, click_count = click_map.get(button_var.get(), ("left", 1))

        try:
            region = parse_region()
        except Exception as exc:
            messagebox.showerror("Invalid region", str(exc), parent=win)
            return

        state["stop_event"].clear()
        set_controls_running(True)
        set_status("Scanning for the reference image...")
        state["thread"] = threading.Thread(
            target=worker,
            args=(
                state["image_path"],
                confidence,
                mode_name,
                burst_count,
                interval_seconds,
                button_name,
                click_count,
                grayscale_var.get(),
                region,
                offset_x,
                offset_y,
                settle_delay,
                beep_var.get(),
            ),
            daemon=True,
        )
        state["thread"].start()

    def stop_scan():
        if state["thread"] and state["thread"].is_alive():
            state["stop_event"].set()
            set_status("Stop requested.")

    def close_window():
        state["stop_event"].set()
        win.destroy()

    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("PC.Accent.TButton", background=_ACCENT, foreground="white", padding=(14, 8), font=("Segoe UI", 10, "bold"))
    style.map("PC.Accent.TButton", background=[("active", "#115e59"), ("disabled", "#94a3b8")])
    style.configure("PC.Danger.TButton", background=_DANGER, foreground="white", padding=(12, 8), font=("Segoe UI", 10, "bold"))
    style.map("PC.Danger.TButton", background=[("active", "#991b1b"), ("disabled", "#94a3b8")])
    style.configure("PC.Secondary.TButton", background="#e2e8f0", foreground="#0f172a", padding=(12, 7), font=("Segoe UI", 10))
    style.map("PC.Secondary.TButton", background=[("active", "#cbd5e1")])

    shell, _photo_canvas = _create_scrollable_shell(win, _BG, min_width=760, padx=18, pady=18)
    shell.columnconfigure(0, weight=1)

    hero = tk.Frame(shell, bg=_HERO_BG, padx=20, pady=16)
    hero.grid(row=0, column=0, sticky="ew")
    tk.Label(hero, text="Photo Clicker", bg=_HERO_BG, fg=_HERO_FG, font=("Segoe UI", 16, "bold")).pack(anchor="w")
    tk.Label(
        hero,
        text="Find a reference image, click with optional offsets, and narrow the scan area when you need faster automation.",
        bg=_HERO_BG,
        fg=_HERO_SUB,
        font=("Segoe UI", 9),
        wraplength=680,
        justify=LEFT,
    ).pack(anchor="w", pady=(2, 0))

    tool_card = tk.Frame(shell, bg=_CARD_BG, padx=16, pady=16, highlightbackground=_BORDER, highlightthickness=1)
    tool_card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
    tool_card.columnconfigure(1, weight=1)
    tool_card.columnconfigure(3, weight=1)
    tk.Label(tool_card, text="Scan preset", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
    preset_combo = ttk.Combobox(
        tool_card,
        textvariable=preset_var,
        values=("Balanced", "Precision Hunt", "Fast Watch", "Burst Sweep"),
        state="readonly",
        width=18,
    )
    preset_combo.grid(row=0, column=1, sticky="w", pady=(0, 10))
    ttk.Button(tool_card, text="Apply Preset", style="PC.Secondary.TButton", command=apply_scan_preset).grid(row=0, column=2, sticky="w", padx=(10, 8), pady=(0, 10))
    ttk.Button(tool_card, text="Open Image Folder", style="PC.Secondary.TButton", command=open_image_folder).grid(row=0, column=3, sticky="e", pady=(0, 10))
    tk.Label(tool_card, text="Focus zone size", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w")
    ttk.Entry(tool_card, textvariable=focus_size_var, width=12).grid(row=1, column=1, sticky="w")
    ttk.Button(tool_card, text="Reset To Screen", style="PC.Secondary.TButton", command=lambda: set_full_screen_region(set_mode=True)).grid(row=1, column=2, sticky="w", padx=(10, 8))
    ttk.Button(tool_card, text="Focus Near Cursor", style="PC.Secondary.TButton", command=focus_region_near_cursor).grid(row=1, column=3, sticky="e")

    card = tk.Frame(shell, bg=_CARD_BG, padx=16, pady=16, highlightbackground=_BORDER, highlightthickness=1)
    card.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
    card.columnconfigure(1, weight=1)
    card.columnconfigure(3, weight=1)

    tk.Label(card, text="Reference image", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
    tk.Label(card, textvariable=filepath_var, bg=_CARD_BG, fg="#475569", font=("Segoe UI", 10), wraplength=360, justify=LEFT).grid(row=0, column=1, columnspan=2, sticky="w", pady=(0, 8))
    ttk.Button(card, text="Browse...", style="PC.Secondary.TButton", command=pick_image).grid(row=0, column=3, sticky="e", pady=(0, 8))

    tk.Label(card, text="Preview", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="nw", pady=(0, 12))
    thumb_label = tk.Label(
        card,
        text="(no image)",
        bg="#e2e8f0",
        fg="#64748b",
        width=24,
        height=8,
        relief="solid",
        bd=1,
        font=("Segoe UI", 9),
    )
    thumb_label.grid(row=1, column=1, sticky="w", pady=(0, 12))
    insight_frame = tk.Frame(card, bg=_CARD_BG)
    insight_frame.grid(row=1, column=2, columnspan=2, sticky="nsew", padx=(14, 0), pady=(0, 12))
    insight_frame.columnconfigure(0, weight=1)
    tk.Label(insight_frame, text="Region summary", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
    tk.Label(insight_frame, textvariable=region_summary_var, bg=_CARD_BG, fg="#475569", font=("Segoe UI", 9), wraplength=270, justify=LEFT).grid(row=1, column=0, sticky="w", pady=(4, 10))
    tk.Label(
        insight_frame,
        text="Use click offsets when the image itself is not the exact point you want to press.",
        bg=_CARD_BG,
        fg="#475569",
        font=("Segoe UI", 9),
        wraplength=270,
        justify=LEFT,
    ).grid(row=2, column=0, sticky="w")

    tk.Label(card, text="Confidence (0-1)", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 8))
    ttk.Entry(card, textvariable=confidence_var, width=12).grid(row=2, column=1, sticky="w", pady=(0, 8))
    tk.Label(card, text="Click type", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=2, column=2, sticky="w", padx=(14, 0), pady=(0, 8))
    ttk.Combobox(card, textvariable=button_var, state="readonly", width=18, values=("Left Click", "Right Click", "Middle Click", "Double Left Click", "Double Right Click")).grid(row=2, column=3, sticky="w", pady=(0, 8))

    tk.Label(card, text="Mode", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 8))
    mode_combo = ttk.Combobox(card, textvariable=mode_var, state="readonly", width=18, values=("Click Once", "Burst Count", "Continuous Watch"))
    mode_combo.grid(row=3, column=1, sticky="w", pady=(0, 8))
    tk.Label(card, text="Burst count", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=3, column=2, sticky="w", padx=(14, 0), pady=(0, 8))
    burst_entry = ttk.Entry(card, textvariable=burst_var, width=12, state=DISABLED)
    burst_entry.grid(row=3, column=3, sticky="w", pady=(0, 8))

    tk.Label(card, text="Scan interval (sec)", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 8))
    ttk.Entry(card, textvariable=interval_var, width=12).grid(row=4, column=1, sticky="w", pady=(0, 8))
    tk.Label(card, text="Stop hotkey", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=4, column=2, sticky="w", padx=(14, 0), pady=(0, 8))
    ttk.Entry(card, textvariable=hotkey_var, width=12).grid(row=4, column=3, sticky="w", pady=(0, 8))

    tk.Label(card, text="Click offset X / Y", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=5, column=0, sticky="w", pady=(0, 8))
    offset_row = tk.Frame(card, bg=_CARD_BG)
    offset_row.grid(row=5, column=1, sticky="w", pady=(0, 8))
    ttk.Entry(offset_row, textvariable=offset_x_var, width=8).grid(row=0, column=0, padx=(0, 6))
    ttk.Entry(offset_row, textvariable=offset_y_var, width=8).grid(row=0, column=1)
    tk.Label(card, text="Settle delay (sec)", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=5, column=2, sticky="w", padx=(14, 0), pady=(0, 8))
    ttk.Entry(card, textvariable=settle_delay_var, width=12).grid(row=5, column=3, sticky="w", pady=(0, 8))

    ttk.Checkbutton(card, text="Grayscale matching", variable=grayscale_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 8))
    ttk.Checkbutton(card, text="Beep when a match is clicked", variable=beep_var).grid(row=6, column=2, columnspan=2, sticky="w", pady=(0, 8))

    tk.Label(card, text="Region", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=7, column=0, sticky="w", pady=(0, 8))
    region_combo = ttk.Combobox(card, textvariable=region_var, state="readonly", width=18, values=("Full Screen", "Custom Region"))
    region_combo.grid(row=7, column=1, sticky="w", pady=(0, 8))
    tk.Label(
        card,
        text="Preset focus creates a square region around your cursor for faster hunts.",
        bg=_CARD_BG,
        fg="#475569",
        font=("Segoe UI", 9),
        wraplength=300,
        justify=LEFT,
    ).grid(row=7, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(0, 8))

    region_frame = ttk.LabelFrame(card, text="Custom region", padding=10)
    region_frame.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(4, 10))
    ttk.Label(region_frame, text="X1").grid(row=0, column=0, sticky="w")
    rx1_entry = ttk.Entry(region_frame, textvariable=rx1_var, width=8, state=DISABLED)
    rx1_entry.grid(row=0, column=1, padx=(0, 10))
    ttk.Label(region_frame, text="Y1").grid(row=0, column=2, sticky="w")
    ry1_entry = ttk.Entry(region_frame, textvariable=ry1_var, width=8, state=DISABLED)
    ry1_entry.grid(row=0, column=3, padx=(0, 10))
    ttk.Label(region_frame, text="X2").grid(row=0, column=4, sticky="w")
    rx2_entry = ttk.Entry(region_frame, textvariable=rx2_var, width=8, state=DISABLED)
    rx2_entry.grid(row=0, column=5, padx=(0, 10))
    ttk.Label(region_frame, text="Y2").grid(row=0, column=6, sticky="w")
    ry2_entry = ttk.Entry(region_frame, textvariable=ry2_var, width=8, state=DISABLED)
    ry2_entry.grid(row=0, column=7, padx=(0, 10))
    ttk.Button(region_frame, text="Use Full Screen", style="PC.Secondary.TButton", command=lambda: set_full_screen_region(set_mode=True)).grid(row=1, column=0, columnspan=4, sticky="w", pady=(10, 0))
    ttk.Button(region_frame, text="Focus Near Cursor", style="PC.Secondary.TButton", command=focus_region_near_cursor).grid(row=1, column=4, columnspan=4, sticky="e", pady=(10, 0))

    button_row = tk.Frame(card, bg=_CARD_BG)
    button_row.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(6, 0))
    start_btn = ttk.Button(button_row, text="Start Scan", style="PC.Accent.TButton", command=start_scan)
    start_btn.grid(row=0, column=0, padx=(0, 8))
    stop_btn = ttk.Button(button_row, text="Stop", style="PC.Danger.TButton", command=stop_scan, state=DISABLED)
    stop_btn.grid(row=0, column=1)

    status_frame = tk.Frame(shell, bg=_STATUS_BG, padx=16, pady=12)
    status_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))
    tk.Label(status_frame, text="Status", bg=_STATUS_BG, fg=_HERO_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
    tk.Label(status_frame, textvariable=status_var, bg=_STATUS_BG, fg=_STATUS_FG, font=("Segoe UI", 10), wraplength=680, justify=LEFT).grid(row=1, column=0, sticky="w", pady=(4, 0))
    tk.Label(status_frame, textvariable=stats_var, bg=_STATUS_BG, fg=_STATUS_FG, font=("Segoe UI", 9), wraplength=680, justify=LEFT).grid(row=2, column=0, sticky="w", pady=(4, 0))

    for tracked_var in (region_var, rx1_var, ry1_var, rx2_var, ry2_var):
        tracked_var.trace_add("write", update_region_summary)
    preset_combo.bind("<<ComboboxSelected>>", apply_scan_preset)
    mode_combo.bind("<<ComboboxSelected>>", toggle_burst)
    region_combo.bind("<<ComboboxSelected>>", toggle_region)

    toggle_burst()
    toggle_region()
    pump_queue()
    win.protocol("WM_DELETE_WINDOW", close_window)
    if owner is None:
        win.mainloop()


def Colour_Clicker():
    """Advanced Colour Clicker with scrollable tools, recent swatches, and scan presets."""

    if not _ensure_dependencies("Advanced Colour Clicker", ["pyautogui", "keyboard"], parent=tk._default_root):
        return
    if ImageGrab is None:
        _show_dependency_error("Advanced Colour Clicker", ["Pillow"], parent=tk._default_root)
        return

    _BG = "#edf0f7"
    _CARD_BG = "#f8fafc"
    _BORDER = "#bfd0e5"
    _HERO_BG = "#1e293b"
    _HERO_FG = "#f8fafc"
    _HERO_SUB = "#94a3b8"
    _LABEL_FG = "#0f172a"
    _ACCENT = "#0f766e"
    _DANGER = "#b91c1c"

    owner = tk._default_root
    master = tk.Toplevel(owner) if owner else tk.Tk()
    master.title("Advanced Colour Clicker")
    master.geometry("780x820+300+100")
    master.minsize(720, 700)
    master.attributes("-topmost", True)
    master.configure(bg=_BG)
    try:
        master.iconbitmap(_resource_path("favicon.ico"))
    except Exception:
        pass

    try:
        import numpy as np

        has_numpy = True
    except ImportError:
        has_numpy = False

    try:
        from PIL import Image as PILImage, ImageTk as PILImageTk

        has_pil_ui = True
    except ImportError:
        PILImage = None
        PILImageTk = None
        has_pil_ui = False

    try:
        screen_width, screen_height = pyautogui.size()
    except Exception:
        screen_width, screen_height = 1920, 1080

    state = {
        "thread": None,
        "stop_event": threading.Event(),
        "is_sampling": False,
        "loupe_win": None,
        "loupe_canvas": None,
        "sample_hotkey": None,
        "history": [],
    }
    ui_queue = queue.Queue()

    colour_var = tk.StringVar(value="#FFFFFF")
    tolerance_var = tk.StringVar(value="8")
    x_start_var = tk.StringVar(value="0")
    y_start_var = tk.StringVar(value="0")
    x_end_var = tk.StringVar(value=str(screen_width))
    y_end_var = tk.StringVar(value=str(screen_height))
    scan_step_var = tk.StringVar(value="2")
    interval_var = tk.StringVar(value="0.50")
    button_var = tk.StringVar(value="Left Click")
    mode_var = tk.StringVar(value="First Match")
    hotkey_var = tk.StringVar(value="esc")
    preset_var = tk.StringVar(value="Balanced")
    max_clicks_var = tk.StringVar(value="25")
    focus_size_var = tk.StringVar(value="320")
    status_var = tk.StringVar(value="Ready. Sample a colour or select an area.")
    stats_var = tk.StringVar(value="No scans yet.")
    region_summary_var = tk.StringVar(value="Full screen scan ready.")
    rgb_summary_var = tk.StringVar(value="RGB 255, 255, 255")

    def set_status(message):
        ui_queue.put(("status", message))

    def set_stats(message):
        ui_queue.put(("stats", message))

    def pump_ui_queue():
        try:
            while True:
                action, payload = ui_queue.get_nowait()
                if action == "status":
                    status_var.set(payload)
                elif action == "stats":
                    stats_var.set(payload)
                elif action == "finish":
                    state["thread"] = None
                    scan_btn.configure(state=NORMAL)
                    watch_btn.configure(state=NORMAL)
                    stop_btn.configure(state=DISABLED)
        except queue.Empty:
            pass
        master.after(100, pump_ui_queue)

    def is_valid_hex_colour(value):
        value = value.strip()
        if len(value) != 7 or not value.startswith("#"):
            return False
        return all(ch in "0123456789abcdefABCDEF" for ch in value[1:])

    def remember_colour(value):
        value = value.strip().upper()
        if not is_valid_hex_colour(value):
            return
        if value in state["history"]:
            state["history"].remove(value)
        state["history"].insert(0, value)
        state["history"] = state["history"][:6]
        refresh_history_buttons()

    def refresh_history_buttons():
        for child in history_row.winfo_children():
            child.destroy()
        if not state["history"]:
            tk.Label(
                history_row,
                text="Recent swatches appear here after pipette samples.",
                bg=_CARD_BG,
                fg="#64748b",
                font=("Segoe UI", 9),
            ).grid(row=0, column=0, sticky="w")
            return
        for index, swatch in enumerate(state["history"]):
            tk.Button(
                history_row,
                text=swatch,
                bg=swatch,
                fg="white" if swatch not in ("#FFFFFF", "#F8FAFC", "#FEF3C7") else "#0f172a",
                activebackground=swatch,
                activeforeground="white",
                relief="flat",
                font=("Segoe UI", 8, "bold"),
                command=lambda value=swatch: (colour_var.set(value), update_preview(), set_status(f"Loaded swatch {value}.")),
            ).grid(row=0, column=index, padx=(0, 6), sticky="w")

    def update_region_summary(*_args):
        try:
            x1 = int(x_start_var.get())
            y1 = int(y_start_var.get())
            x2 = int(x_end_var.get())
            y2 = int(y_end_var.get())
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            if width == 0 or height == 0:
                raise ValueError
            region_summary_var.set(f"Region {width} x {height} from {min(x1, x2)}, {min(y1, y2)}.")
        except Exception:
            region_summary_var.set("Enter a valid scan region.")

    def select_area():
        overlay = tk.Toplevel(master)
        overlay.attributes("-alpha", 0.3)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="black")
        overlay.focus_force()
        canvas = tk.Canvas(overlay, cursor="cross", bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        selection = {"x1": 0, "y1": 0, "rect": None}

        def on_down(event):
            selection["x1"], selection["y1"] = event.x, event.y
            selection["rect"] = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="white", width=2)

        def on_move(event):
            if selection["rect"]:
                canvas.coords(selection["rect"], selection["x1"], selection["y1"], event.x, event.y)

        def on_up(event):
            x1, y1, x2, y2 = selection["x1"], selection["y1"], event.x, event.y
            x_start_var.set(str(min(x1, x2)))
            y_start_var.set(str(min(y1, y2)))
            x_end_var.set(str(max(x1, x2)))
            y_end_var.set(str(max(y1, y2)))
            overlay.destroy()
            set_status(f"Region set to ({x_start_var.get()}, {y_start_var.get()}) to ({x_end_var.get()}, {y_end_var.get()}).")

        overlay.bind("<ButtonPress-1>", on_down)
        overlay.bind("<B1-Motion>", on_move)
        overlay.bind("<ButtonRelease-1>", on_up)
        overlay.bind("<Escape>", lambda _event: overlay.destroy())

    def set_full_region():
        x_start_var.set("0")
        y_start_var.set("0")
        x_end_var.set(str(screen_width))
        y_end_var.set(str(screen_height))
        set_status("Scan region reset to the full screen.")

    def focus_region_near_cursor():
        try:
            focus_size = max(40, int(focus_size_var.get()))
        except ValueError:
            messagebox.showerror("Invalid focus size", "Focus size must be a whole number.", parent=master)
            return

        try:
            cursor_x, cursor_y = pyautogui.position()
        except Exception as exc:
            messagebox.showerror("Capture failed", f"Unable to read the cursor position.\n{exc}", parent=master)
            return

        half_size = focus_size // 2
        x_start_var.set(str(max(0, cursor_x - half_size)))
        y_start_var.set(str(max(0, cursor_y - half_size)))
        x_end_var.set(str(min(screen_width, cursor_x + half_size)))
        y_end_var.set(str(min(screen_height, cursor_y + half_size)))
        set_status(f"Focused the region around cursor {cursor_x}, {cursor_y}.")

    def apply_colour_preset(*_args):
        preset_name = preset_var.get()
        preset_map = {
            "Balanced": ("8", "2", "0.50", "First Match", "25"),
            "Pinpoint": ("4", "1", "0.75", "First Match", "10"),
            "Sweep": ("12", "3", "0.25", "All Matches", "40"),
            "Wide Hunt": ("18", "4", "0.60", "All Matches", "0"),
        }
        tolerance_value, step_value, interval_value, mode_name, max_clicks = preset_map.get(
            preset_name,
            preset_map["Balanced"],
        )
        tolerance_var.set(tolerance_value)
        scan_step_var.set(step_value)
        interval_var.set(interval_value)
        mode_var.set(mode_name)
        max_clicks_var.set(max_clicks)
        set_status(f"Preset '{preset_name}' applied.")

    def update_loupe():
        if not state["is_sampling"]:
            return
        try:
            cursor_x, cursor_y = pyautogui.position()
            state["loupe_win"].geometry(f"+{cursor_x + 20}+{cursor_y + 20}")
            if has_pil_ui:
                image = ImageGrab.grab(bbox=(cursor_x - 10, cursor_y - 10, cursor_x + 11, cursor_y + 11)).convert("RGB")
                zoomed = image.resize((147, 147), PILImage.NEAREST)
                photo = PILImageTk.PhotoImage(zoomed)
                state["loupe_canvas"].delete("all")
                state["loupe_canvas"].create_image(0, 0, anchor="nw", image=photo)
                state["loupe_canvas"].image = photo
                state["loupe_canvas"].create_line(73, 0, 73, 147, fill="red")
                state["loupe_canvas"].create_line(0, 73, 147, 73, fill="red")
                red, green, blue = image.getpixel((10, 10))
                state["loupe_win"].title(f"#{red:02X}{green:02X}{blue:02X}")
        except Exception:
            pass
        master.after(30, update_loupe)

    def start_sampling():
        if state["is_sampling"]:
            return
        state["is_sampling"] = True
        set_status("Sample colour: click a pixel. Press ESC to cancel.")
        master.config(cursor="cross")
        loupe_window = tk.Toplevel(master)
        loupe_window.overrideredirect(True)
        loupe_window.attributes("-topmost", True)
        loupe_window.geometry("150x150")
        loupe_window.configure(bg="black", highlightbackground="white", highlightthickness=2)
        loupe_canvas = tk.Canvas(loupe_window, width=147, height=147, bg="black", highlightthickness=0)
        loupe_canvas.pack()
        state["loupe_win"] = loupe_window
        state["loupe_canvas"] = loupe_canvas
        update_loupe()

        def cancel_sampling(status_message="Sampling cancelled."):
            state["is_sampling"] = False
            master.config(cursor="")
            try:
                if state["loupe_win"] and state["loupe_win"].winfo_exists():
                    state["loupe_win"].destroy()
            except Exception:
                pass
            state["loupe_win"] = None
            state["loupe_canvas"] = None
            master.unbind("<Button-1>")
            try:
                if state["sample_hotkey"] is not None and keyboard:
                    keyboard.remove_hotkey(state["sample_hotkey"])
            except Exception:
                pass
            state["sample_hotkey"] = None
            set_status(status_message)

        def perform_sample(_event=None):
            x_pos, y_pos = pyautogui.position()
            image = ImageGrab.grab(bbox=(x_pos, y_pos, x_pos + 1, y_pos + 1)).convert("RGB")
            red, green, blue = image.getpixel((0, 0))
            sampled_hex = "#{:02X}{:02X}{:02X}".format(red, green, blue)
            colour_var.set(sampled_hex)
            remember_colour(sampled_hex)
            update_preview()
            cancel_sampling(status_message=f"Sampled colour {sampled_hex}.")

        master.bind("<Button-1>", perform_sample)
        try:
            state["sample_hotkey"] = keyboard.add_hotkey("esc", lambda: cancel_sampling())
        except Exception:
            state["sample_hotkey"] = None

    def update_preview(*_args):
        try:
            colour_hex = colour_var.get().strip().upper()
            if is_valid_hex_colour(colour_hex):
                preview_box.configure(bg=colour_hex)
                red = int(colour_hex[1:3], 16)
                green = int(colour_hex[3:5], 16)
                blue = int(colour_hex[5:7], 16)
                rgb_summary_var.set(f"RGB {red}, {green}, {blue}")
            else:
                preview_box.configure(bg="#e2e8f0")
                rgb_summary_var.set("Enter a valid hex colour.")
        except Exception:
            pass

    def worker(target_hex, tolerance, bbox, step, mode_name, is_watcher, interval_seconds, button_name, click_count, stop_hotkey, max_clicks_per_scan):
        try:
            target_rgb = tuple(int(target_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            iterations = 0
            total_clicks = 0
            while not state["stop_event"].is_set():
                iterations += 1
                if stop_hotkey:
                    try:
                        if keyboard.is_pressed(stop_hotkey):
                            break
                    except Exception:
                        pass
                image = ImageGrab.grab(bbox=bbox).convert("RGB")
                found_points = []
                if has_numpy:
                    arr = np.array(image)
                    diff = np.abs(arr - target_rgb)
                    match_mask = np.all(diff <= tolerance, axis=-1)
                    match_mask = match_mask[::step, ::step]
                    y_coords, x_coords = np.where(match_mask)
                    for y_pos, x_pos in zip(y_coords, x_coords):
                        found_points.append((bbox[0] + x_pos * step, bbox[1] + y_pos * step))
                else:
                    for y_pos in range(0, image.height, step):
                        for x_pos in range(0, image.width, step):
                            red, green, blue = image.getpixel((x_pos, y_pos))
                            if all(abs(channel - target) <= tolerance for channel, target in zip((red, green, blue), target_rgb)):
                                found_points.append((bbox[0] + x_pos, bbox[1] + y_pos))
                                if mode_name == "First Match":
                                    break
                        if mode_name == "First Match" and found_points:
                            break

                if found_points:
                    if mode_name == "First Match":
                        click_points = found_points[:1]
                    else:
                        click_points = found_points[:max_clicks_per_scan] if max_clicks_per_scan > 0 else found_points
                    for point_x, point_y in click_points:
                        if state["stop_event"].is_set():
                            break
                        pyautogui.click(point_x, point_y, button=button_name, clicks=click_count, interval=0.02 if click_count > 1 else 0.0)
                        total_clicks += 1
                    if mode_name == "All Matches" and max_clicks_per_scan > 0 and len(found_points) > len(click_points):
                        set_status(f"Found {len(found_points)} match(es), clicked the first {len(click_points)}.")
                    else:
                        set_status(f"Found {len(found_points)} match(es).")
                else:
                    set_status(f"No match in scan #{iterations}.")

                set_stats(f"Scans: {iterations} | Clicks: {total_clicks}")
                if not is_watcher:
                    break
                state["stop_event"].wait(interval_seconds)
        except Exception as exc:
            set_status(f"Error: {exc}")
        finally:
            ui_queue.put(("finish", None))

    def start_worker(is_watcher):
        try:
            colour_hex = colour_var.get().strip().upper()
            if not is_valid_hex_colour(colour_hex):
                raise ValueError("Colour must use the format #RRGGBB.")
            tolerance = int(tolerance_var.get())
            step = int(scan_step_var.get())
            interval_seconds = float(interval_var.get())
            max_clicks_per_scan = int(max_clicks_var.get())
            if tolerance < 0:
                raise ValueError("Tolerance must be zero or greater.")
            if step < 1:
                raise ValueError("Scan step must be at least 1.")
            if interval_seconds < 0:
                raise ValueError("Watch interval must be zero or greater.")
            if max_clicks_per_scan < 0:
                raise ValueError("Max clicks per scan must be zero or greater.")

            x1 = int(x_start_var.get())
            y1 = int(y_start_var.get())
            x2 = int(x_end_var.get())
            y2 = int(y_end_var.get())
            left = min(x1, x2)
            top = min(y1, y2)
            right = max(x1, x2)
            bottom = max(y1, y2)
            if right <= left or bottom <= top:
                raise ValueError("Scan region must have width and height greater than zero.")
            bbox = (left, top, right, bottom)

            button_name = "left"
            if "Right" in button_var.get():
                button_name = "right"
            elif "Middle" in button_var.get():
                button_name = "middle"
            click_count = 2 if "Double" in button_var.get() else 1
            stop_hotkey = hotkey_var.get().strip()

            state["stop_event"].clear()
            scan_btn.configure(state=DISABLED)
            watch_btn.configure(state=DISABLED)
            stop_btn.configure(state=NORMAL)
            remember_colour(colour_hex)
            state["thread"] = threading.Thread(
                target=worker,
                args=(
                    colour_hex,
                    tolerance,
                    bbox,
                    step,
                    mode_var.get(),
                    is_watcher,
                    interval_seconds,
                    button_name,
                    click_count,
                    stop_hotkey,
                    max_clicks_per_scan,
                ),
                daemon=True,
            )
            state["thread"].start()
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=master)

    def close_window():
        state["stop_event"].set()
        if state["is_sampling"]:
            master.unbind("<Button-1>")
            try:
                if state["sample_hotkey"] is not None and keyboard:
                    keyboard.remove_hotkey(state["sample_hotkey"])
            except Exception:
                pass
        try:
            if state["loupe_win"] and state["loupe_win"].winfo_exists():
                state["loupe_win"].destroy()
        except Exception:
            pass
        master.destroy()

    style = ttk.Style(master)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("CC.Accent.TButton", background=_ACCENT, foreground="white", padding=(12, 7), font=("Segoe UI", 10, "bold"))
    style.map("CC.Accent.TButton", background=[("active", "#115e59"), ("disabled", "#94a3b8")])
    style.configure("CC.Danger.TButton", background=_DANGER, foreground="white", padding=(12, 7), font=("Segoe UI", 10, "bold"))
    style.map("CC.Danger.TButton", background=[("active", "#991b1b"), ("disabled", "#94a3b8")])
    style.configure("CC.Secondary.TButton", background="#e2e8f0", foreground="#0f172a", padding=(12, 7), font=("Segoe UI", 10))
    style.map("CC.Secondary.TButton", background=[("active", "#cbd5e1")])

    shell, _colour_canvas = _create_scrollable_shell(master, _BG, min_width=780, padx=20, pady=20)
    shell.columnconfigure(0, weight=1)

    hero = tk.Frame(shell, bg=_HERO_BG, padx=20, pady=15)
    hero.grid(row=0, column=0, sticky="ew")
    tk.Label(hero, text="Advanced Colour Clicker", bg=_HERO_BG, fg=_HERO_FG, font=("Segoe UI", 16, "bold")).pack(anchor="w")
    tk.Label(
        hero,
        text="Scan wide regions for a sampled colour, keep recent swatches, and cap how many matches each pass is allowed to click.",
        bg=_HERO_BG,
        fg=_HERO_SUB,
        font=("Segoe UI", 9),
        wraplength=700,
        justify=LEFT,
    ).pack(anchor="w")

    tool_card = tk.Frame(shell, bg=_CARD_BG, padx=15, pady=15, highlightbackground=_BORDER, highlightthickness=1)
    tool_card.grid(row=1, column=0, sticky="ew", pady=(15, 0))
    tool_card.columnconfigure(1, weight=1)
    tool_card.columnconfigure(3, weight=1)
    tk.Label(tool_card, text="Search preset", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
    preset_combo = ttk.Combobox(tool_card, textvariable=preset_var, values=("Balanced", "Pinpoint", "Sweep", "Wide Hunt"), state="readonly", width=18)
    preset_combo.grid(row=0, column=1, sticky="w", pady=(0, 10))
    ttk.Button(tool_card, text="Apply Preset", style="CC.Secondary.TButton", command=apply_colour_preset).grid(row=0, column=2, sticky="w", padx=(10, 8), pady=(0, 10))
    tk.Label(tool_card, text="Focus zone size", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w")
    ttk.Entry(tool_card, textvariable=focus_size_var, width=12).grid(row=1, column=1, sticky="w")
    ttk.Button(tool_card, text="Full Screen", style="CC.Secondary.TButton", command=set_full_region).grid(row=1, column=2, sticky="w", padx=(10, 8))
    ttk.Button(tool_card, text="Focus Near Cursor", style="CC.Secondary.TButton", command=focus_region_near_cursor).grid(row=1, column=3, sticky="e")

    card1 = tk.Frame(shell, bg=_CARD_BG, padx=15, pady=15, highlightbackground=_BORDER, highlightthickness=1)
    card1.grid(row=2, column=0, sticky="ew", pady=(15, 0))
    card1.columnconfigure(1, weight=1)
    tk.Label(card1, text="Target Colour", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
    colour_row = tk.Frame(card1, bg=_CARD_BG)
    colour_row.grid(row=1, column=0, columnspan=2, sticky="ew")
    preview_box = tk.Frame(colour_row, width=40, height=40, relief="solid", bd=1, bg="#FFFFFF")
    preview_box.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))
    preview_box.grid_propagate(False)
    ttk.Entry(colour_row, textvariable=colour_var, width=12).grid(row=0, column=1, sticky="w", padx=(0, 10))
    ttk.Button(colour_row, text="Pipette", style="CC.Secondary.TButton", command=start_sampling).grid(row=0, column=2, sticky="w", padx=(0, 10))
    tk.Label(colour_row, text="Tolerance", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="w")
    ttk.Entry(colour_row, textvariable=tolerance_var, width=8).grid(row=0, column=4, sticky="w")
    tk.Label(colour_row, textvariable=rgb_summary_var, bg=_CARD_BG, fg="#475569", font=("Segoe UI", 9)).grid(row=1, column=1, columnspan=4, sticky="w", pady=(8, 0))
    tk.Label(card1, text="Recent swatches", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(14, 6))
    history_row = tk.Frame(card1, bg=_CARD_BG)
    history_row.grid(row=3, column=0, columnspan=2, sticky="w")

    card2 = tk.Frame(shell, bg=_CARD_BG, padx=15, pady=15, highlightbackground=_BORDER, highlightthickness=1)
    card2.grid(row=3, column=0, sticky="ew", pady=(15, 0))
    tk.Label(card2, text="Scan Region", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
    region_grid = tk.Frame(card2, bg=_CARD_BG)
    region_grid.grid(row=1, column=0, sticky="ew")
    tk.Label(region_grid, text="X1", bg=_CARD_BG).grid(row=0, column=0, padx=(0, 4))
    ttk.Entry(region_grid, textvariable=x_start_var, width=8).grid(row=0, column=1, padx=(0, 8))
    tk.Label(region_grid, text="Y1", bg=_CARD_BG).grid(row=0, column=2, padx=(0, 4))
    ttk.Entry(region_grid, textvariable=y_start_var, width=8).grid(row=0, column=3, padx=(0, 8))
    tk.Label(region_grid, text="X2", bg=_CARD_BG).grid(row=0, column=4, padx=(0, 4))
    ttk.Entry(region_grid, textvariable=x_end_var, width=8).grid(row=0, column=5, padx=(0, 8))
    tk.Label(region_grid, text="Y2", bg=_CARD_BG).grid(row=0, column=6, padx=(0, 4))
    ttk.Entry(region_grid, textvariable=y_end_var, width=8).grid(row=0, column=7, padx=(0, 8))
    ttk.Button(region_grid, text="Select Area", style="CC.Secondary.TButton", command=select_area).grid(row=0, column=8, padx=(6, 6))
    ttk.Button(region_grid, text="Full Screen", style="CC.Secondary.TButton", command=set_full_region).grid(row=0, column=9, padx=(0, 6))
    ttk.Button(region_grid, text="Focus Cursor", style="CC.Secondary.TButton", command=focus_region_near_cursor).grid(row=0, column=10)
    tk.Label(card2, textvariable=region_summary_var, bg=_CARD_BG, fg="#475569", font=("Segoe UI", 9), wraplength=700, justify=LEFT).grid(row=2, column=0, sticky="w", pady=(10, 0))

    card3 = tk.Frame(shell, bg=_CARD_BG, padx=15, pady=15, highlightbackground=_BORDER, highlightthickness=1)
    card3.grid(row=4, column=0, sticky="ew", pady=(15, 0))
    card3.columnconfigure(1, weight=1)
    card3.columnconfigure(3, weight=1)
    tk.Label(card3, text="Mode", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
    ttk.Combobox(card3, textvariable=mode_var, values=("First Match", "All Matches"), state="readonly", width=16).grid(row=0, column=1, sticky="w", pady=(0, 8))
    tk.Label(card3, text="Button", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(14, 0), pady=(0, 8))
    ttk.Combobox(card3, textvariable=button_var, values=("Left Click", "Right Click", "Double Left", "Middle Click"), state="readonly", width=16).grid(row=0, column=3, sticky="w", pady=(0, 8))
    tk.Label(card3, text="Scan step", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 8))
    ttk.Entry(card3, textvariable=scan_step_var, width=12).grid(row=1, column=1, sticky="w", pady=(0, 8))
    tk.Label(card3, text="Watch interval", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=1, column=2, sticky="w", padx=(14, 0), pady=(0, 8))
    ttk.Entry(card3, textvariable=interval_var, width=12).grid(row=1, column=3, sticky="w", pady=(0, 8))
    tk.Label(card3, text="Stop hotkey", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 8))
    ttk.Entry(card3, textvariable=hotkey_var, width=12).grid(row=2, column=1, sticky="w", pady=(0, 8))
    tk.Label(card3, text="Max clicks per scan", bg=_CARD_BG, fg=_LABEL_FG, font=("Segoe UI", 10, "bold")).grid(row=2, column=2, sticky="w", padx=(14, 0), pady=(0, 8))
    ttk.Entry(card3, textvariable=max_clicks_var, width=12).grid(row=2, column=3, sticky="w", pady=(0, 8))
    tk.Label(card3, text=f"Engine: {'NumPy accelerated' if has_numpy else 'pixel-by-pixel fallback'}", bg=_CARD_BG, fg="#475569", font=("Segoe UI", 9)).grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

    button_row = tk.Frame(shell, bg=_BG)
    button_row.grid(row=5, column=0, sticky="w", pady=(20, 0))
    scan_btn = ttk.Button(button_row, text="Single Scan", style="CC.Accent.TButton", command=lambda: start_worker(False))
    scan_btn.grid(row=0, column=0, padx=(0, 10))
    watch_btn = ttk.Button(button_row, text="Watch Region", style="CC.Secondary.TButton", command=lambda: start_worker(True))
    watch_btn.grid(row=0, column=1, padx=(0, 10))
    stop_btn = ttk.Button(button_row, text="Stop", style="CC.Danger.TButton", state=DISABLED, command=lambda: state["stop_event"].set())
    stop_btn.grid(row=0, column=2)

    status_strip = tk.Frame(shell, bg="#0f172a", padx=15, pady=10)
    status_strip.grid(row=6, column=0, sticky="ew", pady=(15, 0))
    tk.Label(status_strip, textvariable=status_var, bg="#0f172a", fg="#f8fafc", font=("Segoe UI", 9), wraplength=700, justify=LEFT).pack(anchor="w")
    tk.Label(status_strip, textvariable=stats_var, bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 8), wraplength=700, justify=LEFT).pack(anchor="w")

    colour_var.trace_add("write", update_preview)
    for tracked_var in (x_start_var, y_start_var, x_end_var, y_end_var):
        tracked_var.trace_add("write", update_region_summary)
    preset_combo.bind("<<ComboboxSelected>>", apply_colour_preset)

    remember_colour(colour_var.get())
    update_region_summary()
    update_preview()
    pump_ui_queue()
    master.protocol("WM_DELETE_WINDOW", close_window)
    if owner is None:
        master.mainloop()

def Locate_Click():
    """Wrapper for the advanced Photo Clicker tool."""
    if not _ensure_dependencies("Locate and Click", ["pyautogui", "keyboard"]):
        return
    Photo_Clicker()


def Mega_Spam():
    if not _ensure_dependencies("Mega Spam", ["pyautogui", "keyboard"]):
        return
    owner = tk._default_root
    master = tk.Toplevel(owner) if owner else tk.Tk()
    master.title("Mega Spam Mode")
    master.geometry("350x200+400+300")
    master.attributes("-topmost", True)
    master.configure(bg="#1e293b")
    
    state = {"spamming": False, "thread": None}
    
    def spam_worker():
        while state["spamming"]:
            if keyboard.is_pressed("esc"):
                state["spamming"] = False
                break
            pyautogui.click()
        btn.config(text="START SPAM", bg="#0f766e")

    def toggle_spam():
        if state["spamming"]:
            state["spamming"] = False
        else:
            state["spamming"] = True
            btn.config(text="STOP (ESC)", bg="#b91c1c")
            state["thread"] = threading.Thread(target=spam_worker, daemon=True)
            state["thread"].start()

    tk.Label(master, text="MEGA SPAM", font=("Segoe UI", 16, "bold"), bg="#1e293b", fg="#f8fafc").pack(pady=(20, 5))
    tk.Label(master, text="Bypasses normal delays for maximum CPS.", font=("Segoe UI", 9), bg="#1e293b", fg="#cbd5e1").pack()
    tk.Label(master, text="Press ESC to force stop.", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#ef4444").pack(pady=(0, 20))
    
    btn = tk.Button(master, text="START SPAM", font=("Segoe UI", 12, "bold"), bg="#0f766e", fg="white", bd=0, command=toggle_spam)
    btn.pack(ipadx=20, ipady=5)

def Coordinates_Finder():
    if not _ensure_dependencies("Coordinates Finder", ["pyautogui"]):
        return
    owner = tk._default_root
    master = tk.Toplevel(owner) if owner else tk.Tk()
    master.title("Live Coordinates")
    master.geometry("250x100+500+100")
    master.attributes("-topmost", True)
    master.configure(bg="#f8fafc")
    
    lbl = tk.Label(master, text="X: 0 | Y: 0", font=("Consolas", 18, "bold"), bg="#f8fafc", fg="#0f172a")
    lbl.pack(expand=True)
    
    def update():
        try:
            x, y = pyautogui.position()
            lbl.config(text=f"X: {x} | Y: {y}")
        except: pass
        master.after(50, update)
        
    update()

def Contact_Page():
    owner = tk._default_root
    master = tk.Toplevel(owner) if owner else tk.Tk()
    master.title("Contact & Feedback")
    master.geometry("400x250+400+300")
    master.configure(bg="#eef2ff")
    
    tk.Label(master, text="We'd love to hear from you!", font=("Segoe UI", 14, "bold"), bg="#eef2ff", fg="#1e3a8a").pack(pady=20)
    
    def open_github(): webbrowser.open("https://github.com/kai9987kai")
    def open_email(): webbrowser.open("mailto:feedback@example.com")
    
    tk.Button(master, text="Visit GitHub Profile", font=("Segoe UI", 10), bg="#1e293b", fg="white", command=open_github).pack(pady=10, ipadx=10, ipady=5)
    tk.Button(master, text="Send Email Feedback", font=("Segoe UI", 10), bg="#0f766e", fg="white", command=open_email).pack(pady=10, ipadx=10, ipady=5)

def Help_Page():
    owner = tk._default_root
    master = tk.Toplevel(owner) if owner else tk.Tk()
    master.title("AutoClicker Help")
    master.geometry("500x400+350+200")
    master.configure(bg="#f8fafc")
    
    txt = tk.Text(master, font=("Segoe UI", 10), bg="#f8fafc", fg="#334155", wrap="word", padx=20, pady=20, bd=0)
    txt.pack(fill="both", expand=True)
    
    help_text = """AutoClicker Innovation Suite Help

1. Basic Clicking:
Set the Target X and Y (or leave empty to click at the current cursor). Set the delay between clicks, and choose the click button. Press Start or use your hotkey.

2. Photo Clicker:
Open from the Tools menu. This allows you to select an image from your disk and the app will scan your screen for it and click it.

3. Colour Clicker:
Advanced mode to click specific pixels. Use the 'Pipette' to sample a colour from your screen.

4. Mega Spam:
Use this mode when you need the absolute maximum clicks per second, ignoring all safety delays.

5. Recording:
Use the 'Record' button in the Quick Tools to capture a sequence of points (press 'R' to capture), then replay them."""
    txt.insert("1.0", help_text)
    txt.config(state="disabled")

def feedback():
    Contact_Page()


def NOTIFICATION():
    try:
        toaster = win10toast.ToastNotifier()
        toaster.show_toast("AutoClicker", APP_VERSION, duration=5, threaded=True, icon_path=_resource_path("favicon.ico"))
        messagebox.showinfo('AutoClicker', APP_VERSION)
    except:
        messagebox.showinfo('AutoClicker', APP_VERSION)
        pass

  
def tutorial():
    Help_Page()

def OldStyleGUI():
    if not _ensure_dependencies("Old Style GUI", ["pyautogui", "keyboard"]):
        return
    class YourGUI(tk.Tk):
        def __init__(self):
            # inherit tkinter's window methods
            tk.Tk.__init__(self)

            tk.Label(self, text="ENTER Y:", background="#e7dff2").grid(row=0, column=2)
            self.inputX = tk.Entry(self)
            self.inputX.grid(row=0, column=1)

            tk.Label(self, text="ENTER X:", background="#e7dff2").grid(row=0, column=0)
            self.inputY = tk.Entry(self)
            self.inputY.grid(row=0, column=3)
            
            self.cmb = ttk.Combobox(self, width="10", values=("Left Click","Right Click","Middle Click","Double Right Click","Double Left Click","Double Middle Click"))
            ttk.Label(self, text="Delay Between clicks", background="#e7dff2", anchor=E).grid(row=7, column=0)
            self.inputdelayentry = tk.StringVar()


            
            self.inputdelayentry.set("0")
        
            
            self.inputdelay = tk.Entry(self, textvariable= self.inputdelayentry).grid(row=7, column=1)


            class TableDropDown(ttk.Combobox):
                def __init__(self, parent):
                    self.current_table = tk.StringVar() # create variable for table
                    ttk.Combobox.__init__(self, parent)#  init widget
                    self.config(textvariable = self.current_table, state = "readonly", values = ["Customers", "Pets", "Invoices", "Prices"])
                    self.current(0) # index of values for current table
                    self.place(x = 50, y = 50, anchor = "w") # place drop down box

            ttk.Label(self, text="""Choose the left or
right mouse button""", background="#e7dff2", anchor=E).grid(row=1, column=0)
            self.cmb.grid(row=1, column=1, sticky="ew")
            self.cmb.current(0)


            
            # Start Button ⬇
            tk.Button(self, text="start", fg='green', command=self.startclick).grid(row=7, column=0)
            # close button ⬇
            tk.Button(self, text="exit!", fg='red', command=self.EXITME).grid(row=7, column=0)

            self.inputhotkey = tk.Entry(self)
            self.inputhotkey.grid(row=1, column=3, columnspan=1)


            def callback():
                webbrowser.open_new(r"https://kai9987kai.github.io/AutoClicker.html")

            def callback2():
                webbrowser.open_new(r"https://github.com/kai9987kai/AutoClicker")

            tk.Button(self, text="ABOUT", command=callback).grid(row=5, column=3, sticky="ew")

            def clicked3():
                your_gui.destroy()
                pyautogui.PAUSE = 0.50
                pyautogui.FAILSAFE = True

                things = []
                root = Tk()
                root.geometry("550x425")

                list_box = Listbox(root, font=(12))
                list_box.config(width=30, height=18)
                list_box.place(x=0, y=0)

                run_btn = Button(root, text="Run List", command=lambda: run_list(), font=(12))
                run_btn.place(x=350, y=15)
                run_btn.config(width=15)

                del_btn = Button(root, text="Delete", command=lambda: delete(list_box), font=(12))
                del_btn.place(x=350, y=105)
                del_btn.config(width=15)

                add_btn = Button(root, text="Add", command=lambda: add(), font=(12))
                add_btn.place(x=350, y=60)
                add_btn.config(width=15)

                x_txt = StringVar()
                y_txt = StringVar()

                x_label = Label(root, text="x", font=(12))
                x_label.place(x=350, y=150)

                x = Entry(root, textvariable=x_txt)
                x.place(x=375, y=150)

                x_txt.set('')
                y_label = Label(root, text="y", font=(12))
                y_label.place(x=350, y=180)

                y = Entry(root, textvariable=y_txt)
                y.place(x=375, y=180)
                y_txt.set('')

                cmb = ttk.Combobox(root, width="15", values=("Left Click","Right Click","Middle Click","Double Right Click","Double Left Click","Double Middle Click"))
                ttk.Label(root, text="""Select whether to right or
left click the list""", anchor=E).place(x=350, y=220)
                cmb.place(x=350, y=265)
                cmb.current(0)

                def add():
                    content_x = x_txt.get()
                    content_y = y_txt.get()
                    closed_str = [content_x, content_y]
                    things.append(closed_str)
                    list_box.delete(0, 'end')
                    for i in range(len(things)):
                        list_box.insert(END, things[i])

                def run_list():
                    x_cords = [item[0] for item in things]
                    y_cords = [item[1] for item in things]

                    for i in range(len(things)):
                        if cmb.get() == "Left Click":
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click()


                        elif cmb.get() == "Right Click":
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(button='right')
                            pyautogui.click()

                        elif cmb.get() == "Middle Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(button='middle')
                            pyautogui.click()
                        elif cmb.get() == "Double Right Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(clicks=2)
                            pyautogui.click(button='right')
                            pyautogui.click()
                        elif cmb.get() == "Double Left Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(clicks=2)
                            pyautogui.click(button='left')
                            pyautogui.click()
                        elif cmb.get() == "Double Middle Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(clicks=2)
                            pyautogui.click(button='middle')
                            pyautogui.click()
            


                def delete(listbox):
                    global things
                    # Delete from Listbox
                    selection = list_box.curselection()
                    list_box.delete(selection[0])
                    # Delete from list that provided it
                    value = eval(list_box.get(selection[0]))
                    ind = things.index(value)
                    del (things[ind])

                popup = Menu(root, tearoff=0)
                popup.add_command(label='Run list', command=run_list)
                popup.add_command(label='Exit', command=self.EXITME)

                def do_popup(event):
                    # display the popup menu
                    try:
                        popup.tk_popup(event.x_root, event.y_root, 0)
                    finally:
                        # make sure to release the grab (Tk 8.0a1 only)
                        popup.grab_release()

                root.bind("<Button-3>", do_popup)

                root.title("AutoClicker - list of coordinates")
                try:
                    root.iconbitmap(_resource_path("favicon.ico"))
                
                except:
                    pass
                root.resizable(False, False)
                root.attributes("-topmost", True)
                root.mainloop()
            def Finder():
                Coordinates_Finder()

            tk.Button(self, text="List Coordinates", command=clicked3).grid(row=7, column=3,sticky="ew")
            tk.Button(self, text="Find Coordinates", command=Finder).grid(row=6, column=3, sticky="ew")
            tk.Button(self, text="Advanced Colour Clicker", command=Colour_Clicker).grid(row=7, column=1, columnspan=2, sticky="ew", padx=4)

            def clicked():
                Contact_Page()

            def settings():
                window = Tk()
                window.title("Settings")
                window.geometry('335x130')
                try:
                    window.iconbitmap(_resource_path("favicon.ico"))
                except:
                    pass
                window.resizable(False, False)
                window.geometry("+0+0")
                window.attributes("-topmost", True)


                def callBackFunc():
                    your_gui.overrideredirect(True)
                    window.destroy()

                def ExitWindow():
                    window.destroy()

                def Full_screen():
                    your_gui.attributes('-fullscreen', True)
                    your_gui.bind('<Escape>', lambda e: root.destroy())
                    window.destroy()
                def Exit_Full_Screen():
                    python = sys.executable
                    os.execl(python, python, * sys.argv)
                def Show_Title_bar():
                    python = sys.executable
                    os.execl(python, python, * sys.argv)
                

                ttk.Label(window, text="Settings").grid(column=0, row=1, sticky="ew")
                Button(window, text="               Exit Settings               ", command=ExitWindow).grid(column=0, row= 6)
                Button(window, text="‍‍FullScreen", command=Full_screen).grid(column=0, row=3, sticky="ew")
                Button(window, text="Exit FullScreen", command=Exit_Full_Screen).grid(column=1, row=3, sticky="ew")
                Button(window, text="Hide Title Bar ", command=callBackFunc).grid(column=0, row=5, sticky="ew")
                Button(window, text="Show Title Bar", command=Show_Title_bar).grid(column=1, row=5, sticky="ew")
                Button(window, text="Restart program", command=Show_Title_bar).grid(column=1, row=6, sticky="ew")

                popup = Menu(your_gui, tearoff=0)
                popup.add_command(label="FullScreen", command=Full_screen)
                popup.add_command(label="Exit FullScreen", command=Exit_Full_Screen)
                popup.add_command(label="Hide Title Bar", command=callBackFunc)
                popup.add_command(label="Show Title Bar", command=Show_Title_bar)
                popup.add_command(label="Restart program", command=Show_Title_bar)
                popup.add_command(label="Exit Settings", command=ExitWindow)

                def do_popup(event):

                    try:

                        popup.tk_popup(event.x_root, event.y_root, 0)
                    finally:
                        popup.grab_release()

                window.bind("<Button-3>", do_popup)

                window.mainloop()


            def OpenModernWindow():
                your_gui.destroy()
                MAINWINDOW_REDESIGNED()

            def clicked2():
                Mega_Spam()

            # Menu Bar!! ⬇
            menu = Menu(self)
            new_item = Menu(menu)
            new_item.add_command(label='About', command=callback)
            new_item.add_command(label='Github Page', command=callback2)
            new_item.add_command(label='List Coordinates', command=clicked3)
            new_item.add_command(label='Version Number', command=NOTIFICATION)
            new_item.add_command(label='Modern Style', command=OpenModernWindow)
            new_item.add_command(label='Auto Clicker Mega Spam', command=clicked2)
            new_item.add_command(label='Coordinates Finder', command=Finder)
            new_item.add_command(label='Send Feedback', command=feedback)
            new_item.add_command(label='Locate and Click', command=Locate_Click)
            new_item.add_command(label='Photo Clicker', command=Photo_Clicker)
            new_item.add_command(label='Advanced Colour Clicker', command=Colour_Clicker)
            new_item.add_command(label='Settings', command=settings)
            new_item.add_separator()
            new_item.add_command(label='Start', command=self.do_conversion)
            new_item.add_command(label='Exit', command=self.EXITME)
            menu.add_cascade(label='Menu', menu=new_item)
            new_item2 = Menu(menu)
            new_item2.add_command(label='Tutorial', command=tutorial)
            new_item2.add_command(label='Contact', command=clicked)
            menu.add_cascade(label='Help', menu=new_item2)
            popup = Menu(self, tearoff=0)
            popup.add_command(label="About", command=callback)
            popup.add_command(label="Send Feedback", command=feedback) 
            popup.add_command(label='GitHub Page', command=callback2)
            popup.add_command(label='Auto Clicker Mega Spam', command=clicked2)
            popup.add_command(label='Version Number', command=NOTIFICATION)
            popup.add_command(label='Modern Style', command=OpenModernWindow)
            popup.add_command(label='Settings', command=settings)
            popup.add_command(label='List of coordinates', command=clicked3)
            popup.add_command(label='Locate and Click', command=Locate_Click)
            popup.add_command(label='Photo Clicker', command=Photo_Clicker)
            popup.add_command(label='Advanced Colour Clicker', command=Colour_Clicker)
            popup.add_command(label='Find Coordinates', command=Finder)
            popup.add_separator()
            popup.add_command(label='Start', command=self.do_conversion)
            popup.add_command(label='Exit', command=self.EXITME)

            def do_popup(event):
                # display the popup menu
                try:
                    popup.tk_popup(event.x_root, event.y_root, 0)
                finally:
                    # make sure to release the grab (Tk 8.0a1 only)
                    popup.grab_release()

            self.bind("<Button-3>", do_popup)
            self.config(menu=menu)
            tk.Label(self, text="Keyboard key to stop clicking:", background="#e7dff2").grid(row=1, column=2)


        def _setup_tray(self):
            try:
                from PIL import Image
                image = Image.open(_resource_path("favicon.ico"))
                menu = (
                    item('Restore', self._restore_from_tray),
                    item('Start Clicker', self.startclick),
                    item('Stop Clicker', self.stopclick),
                    item('Exit', self.EXITME)
                )
                self.tray_icon = pystray.Icon("autoclicker", image, "AutoClicker", menu)
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
            except:
                pass

        def _restore_from_tray(self, icon=None, item=None):
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)

        def _minimize_to_tray(self):
            self.withdraw()
            if not hasattr(self, 'tray_icon'):
                self._setup_tray()

        def EXITME(self):

            YourGUI.destroy(self)

        def startclick(self):
            x1 = threading.Thread(target=self.do_conversion, daemon=True)
            x1.start() 
        def do_conversion(self):
            if self.cmb.get() == "Left Click":
                y = self.inputY.get()
                x = self.inputX.get()
                    
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:
                    
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                    # strtoint("crashmE!")
                while running:
                    pyautogui.FAILSAFE = False # disables the fail-safe
                    pyautogui.click(x, y)
                                        
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                        else:
                            pass
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            elif self.cmb.get() == "Right Click":
                
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:

                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                    # strtoint("crashmE!")
                        
                while running:
                    pyautogui.FAILSAFE = False # disables the fail-safe
                    pyautogui.click(button='right')
                    pyautogui.click(x, y)
                     
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
                    
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                        else:
                            pass
            elif self.cmb.get() == "Middle Click":
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    x = int(x)
                    y = int(y)
                except:
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(button='middle')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            elif self.cmb.get() == "Double Right Click":
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    x = int(x)
                    y = int(y)
                except:
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(clicks=2)
                    pyautogui.click(button='right')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            elif self.cmb.get() == "Double Left Click":
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    x = int(x)
                    y = int(y)
                except:
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(clicks=2)
                    pyautogui.click(button='left')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            elif self.cmb.get() == "Double Middle Click":
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    x = int(x)
                    y = int(y)
                except:
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(clicks=2)
                    pyautogui.click(button='middle')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break

        def do_hotkey(self):
            hotkey = self.inputhotkey.get()

    if __name__ == '__main__':
        your_gui = YourGUI()
        your_gui.geometry("+300+300")
        your_gui.attributes("-topmost", True)
        your_gui.title('AutoClicker')  # Set title
        try:
            your_gui.iconbitmap(_resource_path("favicon.ico"))
        except:
            pass
        your_gui.resizable(False, False)
        your_gui.configure(background="#e7dff2")
        your_gui.mainloop()

class Coordinates():
    replayBtn = (100, 350)


def MAINWINDOW_NEWSTYLE():
    if not _ensure_dependencies("AutoClicker", ["pyautogui", "keyboard"]):
        return
    class YourGUI(tk.Tk):
        def __init__(self):
            tk.Tk.__init__(self)
            ttk.Label(self, text="ENTER Y:", background="#e7dff2", anchor=E).grid(row=0, column=2)
            ttk.Label(self, text="Delay Between clicks", background="#e7dff2", anchor=E).grid(row=7, column=0)
            self.inputdelayentry = tk.StringVar()


            
            self.inputdelayentry.set("0")
        
            
            self.inputdelay = ttk.Entry(self, textvariable= self.inputdelayentry).grid(row=7, column=1)
            
             
            
            
            self.inputX = ttk.Entry(self)
            self.inputX.grid(row=0, column=1)
            
            self.cmb = ttk.Combobox(self, width="15", values=("Left Click","Right Click","Middle Click","Double Right Click","Double Left Click","Double Middle Click"))
            
            class TableDropDown(ttk.Combobox):
                def __init__(self, parent):
                    
                    self.current_table = tk.StringVar() # create variable for table
                    ttk.Combobox.__init__(self, parent)#  init widget
                    self.config(textvariable = self.current_table, state = "readonly", values = ["Customers", "Pets", "Invoices", "Prices"])
                    self.current(0) # index of values for current table
                    self.place(x = 50, y = 50, anchor = "w") # place drop down box

            ttk.Label(self, text="""Choose the left or
right mouse button""", background="#e7dff2", anchor=E).grid(row=1, column=0)
            self.cmb.grid(row=1, column=1, sticky="ew")
            self.cmb.current(0)



            
    
            
            ttk.Label(self, text="ENTER X:", background="#e7dff2").grid(row=0, column=0)
            self.inputY = ttk.Entry(self)
            self.inputY.grid(row=0, column=3)
            # Start Button ⬇
            ttk.Button(self, text="start", command=self.startclick).grid(row=7, column=0)
            # close button ⬇
            ttk.Button(self, text="exit!", command=self.EXITME).grid(row=7, column=0)
            self.inputhotkey = ttk.Entry(self)
            self.inputhotkey.grid(row=1, column=3, columnspan=1)


            def callback():
                webbrowser.open_new(r"https://kai9987kai.github.io/AutoClicker.html")

            def callback2():
                webbrowser.open_new(r"https://github.com/kai9987kai/AutoClicker")

            ttk.Button(self, text="ABOUT", command=callback).grid(row=5, column=3, sticky="ew")

            def clicked3():
                your_gui.destroy()
                pyautogui.PAUSE = 0.50
                pyautogui.FAILSAFE = True

                things = []
                root = Tk()
                root.geometry("600x400")

                list_box = Listbox(root, font=(12))
                list_box.config(width=30, height=18)
                list_box.place(x=0, y=0)

                run_btn = ttk.Button(root, text="Run List", command=lambda: run_list())
                run_btn.place(x=350, y=20)
                run_btn.config(width=15)

                del_btn = ttk.Button(root, text="Delete", command=lambda: delete(list_box))
                del_btn.place(x=350, y=80)
                del_btn.config(width=15)

                add_btn = ttk.Button(root, text="Add", command=lambda: add())
                add_btn.place(x=350, y=50)
                add_btn.config(width=15)

                x_txt = StringVar()
                y_txt = StringVar()

                x_label = Label(root, text="x", font=(12))
                x_label.place(x=350, y=150)

                x = ttk.Entry(root, textvariable=x_txt)
                x.place(x=375, y=150)

                x_txt.set('')
                y_label = Label(root, text="y", font=(12))
                y_label.place(x=350, y=170)

                y = ttk.Entry(root, textvariable=y_txt)
                y.place(x=375, y=180)
                y_txt.set('')


            
                cmb = ttk.Combobox(root, width="15", values=("Left Click","Right Click","Middle Click","Double Right Click","Double Left Click","Double Middle Click"))
                ttk.Label(root, text="""Select whether to right or
left click the list""", anchor=E).place(x=350, y=250)
                cmb.place(x=350, y=300)
                cmb.current(0)
                root.title("AutoClicker - list of coordinates")
                try:
                    root.iconbitmap(_resource_path("favicon.ico"))
                except:
                    pass
                root.resizable(False, False)
                root.attributes("-topmost", True)

                def add():
                    content_x = x_txt.get()
                    content_y = y_txt.get()
                    closed_str = [content_x, content_y]
                    things.append(closed_str)
                    list_box.delete(0, 'end')
                    for i in range(len(things)):
                        list_box.insert(END, things[i])

                def run_list():
                    
                    x_cords = [item[0] for item in things]
                    y_cords = [item[1] for item in things]

                    for i in range(len(things)):
                        
                        if cmb.get() == "Left Click":
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click()


                        elif cmb.get() == "Right Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(button='right')
                            pyautogui.click()

                        elif cmb.get() == "Middle Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(button='middle')
                            pyautogui.click()
                        elif cmb.get() == "Double Right Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(clicks=2)
                            pyautogui.click(button='right')
                            pyautogui.click()
                        elif cmb.get() == "Double Left Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(clicks=2)
                            pyautogui.click(button='left')
                            pyautogui.click()
                        elif cmb.get() == "Double Middle Click":
                            
                            screenWidth, screenHeight = pyautogui.size()
                            currentMouseX, currentMouseY = pyautogui.position()
                            pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                            # print("Gonna Click",x_cords[i],y_cords[i])
                            pyautogui.click(clicks=2)
                            pyautogui.click(button='middle')
                            pyautogui.click()
            
                def delete(listbox):
                    global things
                    # Delete from Listbox
                    selection = list_box.curselection()
                    list_box.delete(selection[0])
                    # Delete from list that provided it
                    value = eval(list_box.get(selection[0]))
                    ind = things.index(value)
                    del (things[ind])

                popup = Menu(root, tearoff=0)
                popup.add_command(label='Run list', command=run_list)
                popup.add_command(label='Exit', command=self.EXITME)

                def do_popup(event):
                    # display the popup menu
                    try:
                        popup.tk_popup(event.x_root, event.y_root, 0)
                    finally:
                        # make sure to release the grab (Tk 8.0a1 only)
                        popup.grab_release()

                root.bind("<Button-3>", do_popup)

                root.mainloop()

            def clicked():
                Contact_Page()

            def clicked2():
                Mega_Spam()
            def Finder():
                Coordinates_Finder()
                

            ttk.Button(self, text="List Coordinates", command=clicked3).grid(row=7, column=3, sticky="ew")
            ttk.Button(self, text="Find Coordinates", command=Finder).grid(row=6, column=3, sticky="ew")
            ttk.Button(self, text="Advanced Colour Clicker", command=Colour_Clicker).grid(row=7, column=1, columnspan=2, sticky="ew", padx=4)

            def settings():
                window = Tk()
                window.title("Settings")
                window.geometry('330x115')
                try:
                    window.iconbitmap(_resource_path("favicon.ico"))
                except:
                    pass
                window.resizable(False, False)
                window.geometry("+0+0")
                window.attributes("-topmost", True)


                def callBackFunc():
                    your_gui.overrideredirect(True)
                    window.destroy()

                def ExitWindow():
                    window.destroy()

                def Full_screen():
                    your_gui.attributes('-fullscreen', True)
                    your_gui.bind('<Escape>', lambda e: root.destroy())
                    window.destroy()
                def Exit_Full_Screen():
                    python = sys.executable
                    os.execl(python, python, * sys.argv)
                def Show_Title_bar():
                    python = sys.executable
                    os.execl(python, python, * sys.argv)
                

                ttk.Label(window, text="Settings").grid(column=0, row=1, sticky="ew")
                ttk.Button(window, text="               Exit Settings               ", command=ExitWindow).grid(column=0, row= 6)
                ttk.Button(window, text="‍‍FullScreen", command=Full_screen).grid(column=0, row=3, sticky="ew")
                ttk.Button(window, text="Exit FullScreen", command=Exit_Full_Screen).grid(column=1, row=3, sticky="ew")
                ttk.Button(window, text="Hide Title Bar ", command=callBackFunc).grid(column=0, row=5, sticky="ew")
                ttk.Button(window, text="Show Title Bar", command=Show_Title_bar).grid(column=1, row=5, sticky="ew")
                ttk.Button(window, text="Restart program", command=Show_Title_bar).grid(column=1, row=6, sticky="ew")

                popup = Menu(your_gui, tearoff=0)
                popup.add_command(label="FullScreen", command=Full_screen)
                popup.add_command(label="Exit FullScreen", command=Exit_Full_Screen)
                popup.add_command(label="Hide Title Bar", command=callBackFunc)
                popup.add_command(label="Show Title Bar", command=Show_Title_bar)
                popup.add_command(label="Restart program", command=Show_Title_bar)
                popup.add_command(label="Exit Settings", command=ExitWindow)

                def do_popup(event):

                    try:

                        popup.tk_popup(event.x_root, event.y_root, 0)
                    finally:
                        popup.grab_release()

                window.bind("<Button-3>", do_popup)

                window.mainloop()

            def OpenOldWindow():
                your_gui.destroy()
                OldStyleGUI()

            # Menu Bar!! ⬇
            menu = Menu(self)
            new_item = Menu(menu)
            new_item.add_command(label='About', command=callback)
            new_item.add_command(label='Github Page', command=callback2)
            new_item.add_command(label='Auto Clicker Mega Spam', command=clicked2)
            new_item.add_command(label='Version Number', command=NOTIFICATION)
            new_item.add_command(label='Old Style GUI', command=OpenOldWindow)
            new_item.add_command(label='Settings', command=settings)
            new_item.add_command(label='List of Coordinates', command=clicked3)
            new_item.add_command(label='Coordinates Finder', command=Finder)
            new_item.add_command(label='Send Feedback', command=feedback)
            new_item.add_command(label='Advanced Colour Clicker', command=Colour_Clicker)
            new_item.add_command(label='Locate and Click', command=Locate_Click)
            new_item.add_command(label='Photo Clicker', command=Photo_Clicker)
            new_item.add_separator()
            new_item.add_command(label='Start', command=self.do_conversion)
            new_item.add_command(label='Exit', command=self.EXITME)

            menu.add_cascade(label='Menu', menu=new_item)
            new_item2 = Menu(menu)
            new_item2.add_command(label='Tutorial', command=tutorial)
            menu.add_cascade(label='Help', menu=new_item2)
            new_item2.add_command(label='Contact', command=clicked)
            self.config(menu=menu)
            tk.Label(self, text="Keyboard key to stop clicking:", background="#e7dff2").grid(row=1, column=2)
            popup = Menu(self, tearoff=0)
            popup.add_command(label="About", command=callback)  # , command=next) etc...
            popup.add_command(label='GitHub Page', command=callback2)
            popup.add_command(label='Send Feedback', command=feedback)
            popup.add_command(label='Locate and Click', command=Locate_Click)
            popup.add_command(label='Photo Clicker', command=Photo_Clicker)
            popup.add_command(label='Auto Clicker Mega Spam', command=clicked2)
            popup.add_command(label='Version Number', command=NOTIFICATION)
            popup.add_command(label='Old Style Gui', command=OpenOldWindow)
            popup.add_command(label='Settings', command=settings)
            popup.add_command(label='List of coordinates', command=clicked3)
            popup.add_command(label='Advanced Colour Clicker', command=Colour_Clicker)
            popup.add_command(label='Find Coordinates', command=Finder)
            popup.add_separator()
            popup.add_command(label='Start', command=self.do_conversion)
            popup.add_command(label='Exit', command=self.EXITME)

            def do_popup(event):
                # display the popup menu
                try:
                    popup.tk_popup(event.x_root, event.y_root, 0)
                finally:
                    # make sure to release the grab (Tk 8.0a1 only)
                    popup.grab_release()

            self.bind("<Button-3>", do_popup)


        def _setup_tray(self):
            try:
                from PIL import Image
                image = Image.open(_resource_path("favicon.ico"))
                menu = (
                    item('Restore', self._restore_from_tray),
                    item('Start Clicker', self.startclick),
                    item('Stop Clicker', self.stopclick),
                    item('Exit', self.EXITME)
                )
                self.tray_icon = pystray.Icon("autoclicker", image, "AutoClicker", menu)
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
            except:
                pass

        def _restore_from_tray(self, icon=None, item=None):
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)

        def _minimize_to_tray(self):
            self.withdraw()
            if not hasattr(self, 'tray_icon'):
                self._setup_tray()

        def EXITME(self):

            YourGUI.destroy(self)

        def startclick(self):
            
            x1 = threading.Thread(target=self.do_conversion, daemon=True)
            x1.start()   
        def do_conversion(self):

     
            if self.cmb.get() == "Left Click":
                
                y = self.inputY.get()
                x = self.inputX.get()
                    
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:
                    
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(x, y)
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        running = False
                        
                    
                    
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                        else:
                            pass
                                
            elif self.cmb.get() == "Right Click":
                
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:

                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False # disables the fail-safe
                    pyautogui.click(button='right')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                        else:
                            pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
                    
            
            elif self.cmb.get() == "Middle Click":
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    x = int(x)
                    y = int(y)
                except:
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(button='middle')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            elif self.cmb.get() == "Double Right Click":
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    x = int(x)
                    y = int(y)
                except:
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(clicks=2)
                    pyautogui.click(button='right')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            elif self.cmb.get() == "Double Left Click":
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    x = int(x)
                    y = int(y)
                except:
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(clicks=2)
                    pyautogui.click(button='left')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            elif self.cmb.get() == "Double Middle Click":
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    x = int(x)
                    y = int(y)
                except:
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(clicks=2)
                    pyautogui.click(button='middle')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            def action():
                YourGUI.destroy()


        def getdelay(self):
            tx = self.getinputdelayentry.get()

        def do_hotkey(self):
            hotkey = self.inputhotkey.get()

    if __name__ == '__main__':
        your_gui = YourGUI()
        your_gui.geometry("+300+300")
        your_gui.attributes("-topmost", True)
        your_gui.title('AutoClicker')  # Set title
        try:
            your_gui.iconbitmap(_resource_path("favicon.ico"))
        except:
            pass
        your_gui.resizable(False, False)
        your_gui.configure(background="#e7dff2")
        your_gui.mainloop()
    time.sleep(0)

def MAINWINDOW_REDESIGNED():
    if not _ensure_dependencies("AutoClicker Control Center", ["pyautogui", "keyboard"]):
        return
    class YourGUI(tk.Tk):
        CLICK_TYPES = DEFAULT_CLICK_TYPES
        DELAY_PRESETS = ("0.00", "0.05", "0.10", "0.25", "0.50")

        def __init__(self):
            tk.Tk.__init__(self)

            try:
                self.base_tk_scaling = float(self.tk.call("tk", "scaling"))
            except Exception:
                self.base_tk_scaling = 1.0

            try:
                self.screen_width, self.screen_height = pyautogui.size()
            except:
                self.screen_width, self.screen_height = 1920, 1080

            self.worker_thread = None
            self.sequence_thread = None
            self.stop_event = threading.Event()
            self.ui_queue = queue.Queue()
            self.stop_reason = "idle"
            self.hotkey_notified = False
            self.was_minimized_for_run = False
            self.active_run_was_dry_run = False

            self.target_x_var = tk.StringVar(value="0")
            self.target_y_var = tk.StringVar(value="0")
            self.click_mode_var = tk.StringVar(value="Left Click")
            self.delay_var = tk.StringVar(value="0.10")
            self.delay_variance_var = tk.StringVar(value="0.00")
            self.jitter_x_var = tk.StringVar(value="0")
            self.jitter_y_var = tk.StringVar(value="0")
            self.countdown_var = tk.StringVar(value="0")
            self.runtime_limit_var = tk.StringVar(value="0")
            self.max_actions_var = tk.StringVar(value="0")
            self.stop_hotkey_var = tk.StringVar(value="esc")
            self.repeat_mode_var = tk.StringVar(value="Infinite")
            self.repeat_count_var = tk.StringVar(value="50")
            self.behaviour_preset_var = tk.StringVar(value="Balanced")
            self.micro_pause_every_var = tk.StringVar(value="0")
            self.micro_pause_duration_var = tk.StringVar(value="0.00")
            self.dry_run_var = tk.BooleanVar(value=False)
            self.pyautogui_failsafe_var = tk.BooleanVar(value=False)
            self.topmost_var = tk.BooleanVar(value=True)
            self.minimize_on_start_var = tk.BooleanVar(value=True)
            self.restore_after_run_var = tk.BooleanVar(value=True)
            self.close_to_tray_var = tk.BooleanVar(value=True)
            self.fullscreen_var = tk.BooleanVar(value=False)
            self.remember_window_geometry_var = tk.BooleanVar(value=True)
            self.window_opacity_var = tk.DoubleVar(value=1.0)
            self.ui_scale_var = tk.DoubleVar(value=1.0)
            self.theme_var = tk.StringVar(value="Light")
            self.profile_name_var = tk.StringVar(value="default")
            self.profile_choice_var = tk.StringVar(value="")
            self.status_var = tk.StringVar(value="Ready. Capture a target and press Start.")
            self.cursor_var = tk.StringVar(value="Cursor: --, --")
            self.screen_var = tk.StringVar(value=f"Screen: {self.screen_width} x {self.screen_height}")
            self.plan_var = tk.StringVar(value="")
            self.run_intelligence_var = tk.StringVar(value="Run intelligence will appear after configuration is valid.")
            self.safety_status_var = tk.StringVar(value="Safety: live clicks | corner fail-safe off | no action cap")
            self.readiness_var = tk.StringVar(value="Readiness: awaiting configuration.")
            self.profile_state_var = tk.StringVar(value="Profile: awaiting configuration.")
            self.session_var = tk.StringVar(value="No clicks sent yet.")
            self.last_run_var = tk.StringVar(value="Idle")
            self.recording_summary_var = tk.StringVar(value="Recording: 0 point(s) | idle")
            self.window_summary_var = tk.StringVar(value="")
            self.preset_summary_var = tk.StringVar(value="")
            self.profile_file = _state_file_path(PROFILE_FILE_NAME)
            self.workspace_file = _state_file_path(WORKSPACE_FILE_NAME)
            self.saved_profiles = {}
            self.activity_history = []
            self.run_reports = []
            self.section_states = {}
            self.section_widgets = {}
            self._workspace_save_job = None
            self.record_hotkey_handle = None
            self.emergency_hotkey_handle = None
            self.tray_icon = None
            
            # New innovative features state
            self.human_like_var = tk.BooleanVar(value=False)
            self.play_sound_var = tk.BooleanVar(value=True)
            self.is_recording = False
            self.is_playing = False
            self.recording_data = []
            self.session_clicks = 0
            self.session_start_time = time.time()
            self.after(1000, self._update_dashboard)

            self._configure_window()
            self._configure_styles()
            self._build_menu()
            self._build_layout()
            self._build_context_menu()
            self._load_profiles_from_disk()
            self._load_workspace_from_disk()
            self._apply_window_preferences()
            self._update_repeat_state()
            self._update_plan_summary()
            self._append_activity("Control Center ready.")

            self.bind("<Button-3>", self._show_context_menu)
            self.bind("<Return>", lambda _event: self.startclick())
            self.protocol("WM_DELETE_WINDOW", self._handle_close_request)
            self.after(100, self._pump_ui_queue)
            self.after(200, self._refresh_live_cursor)
            self.after(50, self._apply_theme)
            
            # Global Emergency Kill-Switch
            try:
                self.emergency_hotkey_handle = keyboard.add_hotkey("ctrl+shift+k", lambda: os._exit(0))
            except: pass

        def _configure_window(self):
            self.title("AutoClicker Control Center")
            self.geometry("1080x760+180+90")
            self.minsize(860, 560)
            self.attributes("-topmost", True)
            self.configure(bg="#dbe7f2")
            try:
                self.iconbitmap(_resource_path("favicon.ico"))
            except:
                pass

        def _configure_styles(self):
            self.style = ttk.Style(self)
            try:
                self.style.theme_use("clam")
            except:
                pass
            self._refresh_ttk_styles(self._theme_palette())

        def _theme_palette(self):
            if self.theme_var.get() == "Dark":
                return {
                    "main_bg": "#0f172a",
                    "card_bg": "#1e293b",
                    "alt_bg": "#111827",
                    "hero_bg": "#020617",
                    "hero_chip_bg": "#1f2937",
                    "hero_fg": "#f8fafc",
                    "hero_sub": "#cbd5e1",
                    "text": "#f8fafc",
                    "sub": "#cbd5e1",
                    "accent": "#14b8a6",
                    "accent_active": "#0f766e",
                    "danger": "#ef4444",
                    "danger_active": "#dc2626",
                    "secondary_bg": "#334155",
                    "secondary_active": "#475569",
                    "secondary_fg": "#e2e8f0",
                    "chip_bg": "#0f172a",
                    "chip_fg": "#7dd3fc",
                    "chip_active": "#1e293b",
                    "border": "#334155",
                    "status_bg": "#020617",
                    "status_fg": "#dbeafe",
                    "list_bg": "#0f172a",
                    "list_fg": "#f8fafc",
                    "select_bg": "#0f766e",
                }
            if self.theme_var.get() == "Ocean":
                return {
                    "main_bg": "#d8edf2",
                    "card_bg": "#f4fbfd",
                    "alt_bg": "#e6f4f7",
                    "hero_bg": "#0b3954",
                    "hero_chip_bg": "#114b6c",
                    "hero_fg": "#f8fafc",
                    "hero_sub": "#d7eef8",
                    "text": "#092c3a",
                    "sub": "#3a6170",
                    "accent": "#0f766e",
                    "accent_active": "#115e59",
                    "danger": "#c2410c",
                    "danger_active": "#9a3412",
                    "secondary_bg": "#d1e7ed",
                    "secondary_active": "#bdd8df",
                    "secondary_fg": "#0b3954",
                    "chip_bg": "#d9eff7",
                    "chip_fg": "#0f4c81",
                    "chip_active": "#c4e4ee",
                    "border": "#9bc6d2",
                    "status_bg": "#0b3954",
                    "status_fg": "#edf9ff",
                    "list_bg": "white",
                    "list_fg": "#092c3a",
                    "select_bg": "#0f766e",
                }
            return {
                "main_bg": "#dbe7f2",
                "card_bg": "#f8fafc",
                "alt_bg": "#edf4ff",
                "hero_bg": "#0f172a",
                "hero_chip_bg": "#1e293b",
                "hero_fg": "white",
                "hero_sub": "#cbd5e1",
                "text": "#0f172a",
                "sub": "#475569",
                "accent": "#0f766e",
                "accent_active": "#115e59",
                "danger": "#b91c1c",
                "danger_active": "#991b1b",
                "secondary_bg": "#e2e8f0",
                "secondary_active": "#cbd5e1",
                "secondary_fg": "#0f172a",
                "chip_bg": "#eff6ff",
                "chip_fg": "#1d4ed8",
                "chip_active": "#dbeafe",
                "border": "#bfd0e5",
                "status_bg": "#0f172a",
                "status_fg": "#cbd5e1",
                "list_bg": "white",
                "list_fg": "#0f172a",
                "select_bg": "#1d4ed8",
            }

        def _refresh_ttk_styles(self, palette):
            self.style.configure(
                "Accent.TButton",
                background=palette["accent"],
                foreground="white",
                padding=(14, 8),
                font=("Segoe UI", 10, "bold"),
            )
            self.style.map(
                "Accent.TButton",
                background=[("active", palette["accent_active"]), ("disabled", "#94a3b8")],
                foreground=[("disabled", "#f8fafc")],
            )
            self.style.configure(
                "Secondary.TButton",
                background=palette["secondary_bg"],
                foreground=palette["secondary_fg"],
                padding=(12, 7),
                font=("Segoe UI", 10),
            )
            self.style.map("Secondary.TButton", background=[("active", palette["secondary_active"])])
            self.style.configure(
                "Danger.TButton",
                background=palette["danger"],
                foreground="white",
                padding=(12, 8),
                font=("Segoe UI", 10, "bold"),
            )
            self.style.map(
                "Danger.TButton",
                background=[("active", palette["danger_active"]), ("disabled", "#94a3b8")],
                foreground=[("disabled", "#f8fafc")],
            )
            self.style.configure(
                "Chip.TButton",
                background=palette["chip_bg"],
                foreground=palette["chip_fg"],
                padding=(10, 4),
                font=("Segoe UI", 9, "bold"),
            )
            self.style.map("Chip.TButton", background=[("active", palette["chip_active"])])
            self.style.configure(
                "App.TCheckbutton",
                background=palette["card_bg"],
                foreground=palette["text"],
                font=("Segoe UI", 10),
            )
            self.style.map("App.TCheckbutton", background=[("active", palette["card_bg"])])
            self.style.configure(
                "Command.TCheckbutton",
                background=palette["alt_bg"],
                foreground=palette["text"],
                font=("Segoe UI", 10, "bold"),
            )
            self.style.map("Command.TCheckbutton", background=[("active", palette["alt_bg"])])
            self.style.configure("App.Horizontal.TScale", background=palette["card_bg"])
            self.style.configure("TEntry", fieldbackground=palette["list_bg"], foreground=palette["list_fg"])
            self.style.configure(
                "TCombobox",
                fieldbackground=palette["list_bg"],
                foreground=palette["list_fg"],
                arrowsize=14,
            )
            self.style.map(
                "TCombobox",
                fieldbackground=[("readonly", palette["list_bg"])],
                foreground=[("readonly", palette["list_fg"])],
                selectbackground=[("readonly", palette["select_bg"])],
                selectforeground=[("readonly", palette["hero_fg"])],
            )

        def _create_card(self, parent, title, subtitle=None):
            card = tk.Frame(parent, bg="#f8fafc", padx=16, pady=16, highlightbackground="#bfd0e5", highlightthickness=1)
            tk.Label(card, text=title, bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 12, "bold")).pack(anchor="w")
            if subtitle:
                tk.Label(card, text=subtitle, bg="#f8fafc", fg="#475569", font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
            body = tk.Frame(card, bg="#f8fafc")
            body.pack(fill="both", expand=True, pady=(12, 0))
            return card, body

        def _create_dropdown_section(self, parent, key, title, subtitle, start_open=False):
            card = tk.Frame(parent, bg="#f8fafc", padx=16, pady=16, highlightbackground="#bfd0e5", highlightthickness=1)
            card.columnconfigure(0, weight=1)

            header = tk.Frame(card, bg="#f8fafc")
            header.grid(row=0, column=0, sticky="ew")
            header.columnconfigure(0, weight=1)

            tk.Label(header, text=title, bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(header, text=subtitle, bg="#f8fafc", fg="#475569", font=("Segoe UI", 9), wraplength=620, justify=LEFT).grid(row=1, column=0, sticky="w", pady=(2, 0))
            toggle_button = ttk.Button(header, text="", style="Secondary.TButton", command=lambda section_key=key: self._toggle_dropdown_section(section_key))
            toggle_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

            body = tk.Frame(card, bg="#f8fafc")
            body.grid(row=1, column=0, sticky="ew", pady=(12, 0))

            self.section_widgets[key] = {
                "card": card,
                "body": body,
                "button": toggle_button,
                "title": title,
            }
            self._set_dropdown_state(key, start_open)
            return card, body

        def _set_dropdown_state(self, key, is_open):
            widgets = self.section_widgets.get(key)
            if not widgets:
                return

            self.section_states[key] = bool(is_open)
            if is_open:
                widgets["body"].grid()
                widgets["button"].configure(text="Hide")
            else:
                widgets["body"].grid_remove()
                widgets["button"].configure(text="Open")
            self.after_idle(self._update_main_scroll_region)

        def _toggle_dropdown_section(self, key):
            self._set_dropdown_state(key, not self.section_states.get(key, False))

        def _expand_all_sections(self):
            for section_key in tuple(self.section_widgets):
                self._set_dropdown_state(section_key, True)

        def _collapse_all_sections(self):
            for section_key in tuple(self.section_widgets):
                if section_key != "quick_start":
                    self._set_dropdown_state(section_key, False)

        def _refresh_preset_summary(self):
            descriptions = {
                "Balanced": "General purpose mix of speed and safety with light variation.",
                "Precision": "Slower, cleaner clicks with zero jitter and zero delay variance.",
                "Burst Sprint": "Short, aggressive output tuned for bursts and rapid button spam.",
                "Human Mimic": "More natural timing, broader jitter, and optional micro-break pacing.",
            }
            self.preset_summary_var.set(
                descriptions.get(self.behaviour_preset_var.get(), "Custom run profile.")
            )

        def _apply_behaviour_preset(self):
            preset_name = self.behaviour_preset_var.get()
            preset_map = {
                "Balanced": {
                    "delay": "0.10",
                    "delay_variance": "0.02",
                    "jitter_x": "1",
                    "jitter_y": "1",
                    "human_like": False,
                    "micro_pause_every": "0",
                    "micro_pause_duration": "0.00",
                },
                "Precision": {
                    "delay": "0.20",
                    "delay_variance": "0.00",
                    "jitter_x": "0",
                    "jitter_y": "0",
                    "human_like": False,
                    "micro_pause_every": "0",
                    "micro_pause_duration": "0.00",
                },
                "Burst Sprint": {
                    "delay": "0.03",
                    "delay_variance": "0.00",
                    "jitter_x": "0",
                    "jitter_y": "0",
                    "human_like": False,
                    "micro_pause_every": "30",
                    "micro_pause_duration": "0.15",
                },
                "Human Mimic": {
                    "delay": "0.18",
                    "delay_variance": "0.05",
                    "jitter_x": "4",
                    "jitter_y": "4",
                    "human_like": True,
                    "micro_pause_every": "10",
                    "micro_pause_duration": "0.40",
                },
            }

            preset = preset_map.get(preset_name)
            if not preset:
                return

            self.delay_var.set(preset["delay"])
            self.delay_variance_var.set(preset["delay_variance"])
            self.jitter_x_var.set(preset["jitter_x"])
            self.jitter_y_var.set(preset["jitter_y"])
            self.human_like_var.set(preset["human_like"])
            self.micro_pause_every_var.set(preset["micro_pause_every"])
            self.micro_pause_duration_var.set(preset["micro_pause_duration"])
            self._refresh_preset_summary()
            self.status_var.set(f"Applied '{preset_name}' preset.")
            self._append_activity(f"Behaviour preset applied: {preset_name}.")
            self._update_plan_summary()
            self._schedule_workspace_save()

        def _apply_safety_preset(self, preset_name):
            preset = SAFETY_PRESETS.get(preset_name)
            if not preset:
                return

            self.dry_run_var.set(bool(preset["dry_run"]))
            self.pyautogui_failsafe_var.set(bool(preset["pyautogui_failsafe"]))
            self.max_actions_var.set(str(preset["max_actions"]))
            self.status_var.set(f"Applied safety preset '{preset_name}'.")
            self._append_activity(f"Safety preset applied: {preset_name}.")
            self._update_plan_summary()
            self._schedule_workspace_save()

        def _build_layout(self):
            self.main_shell_min_width = 1180

            scroll_host = tk.Frame(self, bg="#dbe7f2")
            scroll_host.pack(fill="both", expand=True)
            scroll_host.columnconfigure(0, weight=1)
            scroll_host.rowconfigure(0, weight=1)

            self.main_canvas = tk.Canvas(scroll_host, bg="#dbe7f2", highlightthickness=0, bd=0)
            self.main_canvas.grid(row=0, column=0, sticky="nsew")

            main_v_scroll = ttk.Scrollbar(scroll_host, orient="vertical", command=self.main_canvas.yview)
            main_v_scroll.grid(row=0, column=1, sticky="ns")
            main_h_scroll = ttk.Scrollbar(scroll_host, orient="horizontal", command=self.main_canvas.xview)
            main_h_scroll.grid(row=1, column=0, sticky="ew")
            self.main_canvas.configure(yscrollcommand=main_v_scroll.set, xscrollcommand=main_h_scroll.set)

            self.scroll_frame = tk.Frame(self.main_canvas, bg="#dbe7f2")
            self.main_canvas_window = self.main_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
            self.scroll_frame.bind("<Configure>", self._update_main_scroll_region)
            self.main_canvas.bind("<Configure>", self._handle_main_canvas_configure)
            self._bind_main_scroll_support()

            shell = tk.Frame(self.scroll_frame, bg="#dbe7f2", padx=18, pady=18)
            shell.grid(row=0, column=0, sticky="nsew")
            shell.columnconfigure(0, weight=1)

            hero = tk.Frame(shell, bg="#0f172a", padx=20, pady=18)
            hero.grid(row=0, column=0, sticky="ew")
            hero.columnconfigure(0, weight=1)

            tk.Label(hero, text="AutoClicker Control Center", bg="#0f172a", fg="white", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(
                hero,
                text="Dropdown-driven cockpit with fast actions on top and deeper controls hidden until you need them.",
                bg="#0f172a",
                fg="#cbd5e1",
                font=("Segoe UI", 10),
            ).grid(row=1, column=0, sticky="w", pady=(4, 0))

            badge_frame = tk.Frame(hero, bg="#0f172a")
            badge_frame.grid(row=0, column=1, rowspan=2, sticky="e")
            tk.Label(badge_frame, textvariable=self.cursor_var, bg="#1e293b", fg="#e2e8f0", font=("Segoe UI", 10, "bold"), padx=10, pady=6).grid(row=0, column=0, padx=(0, 8))
            tk.Label(badge_frame, textvariable=self.screen_var, bg="#1e293b", fg="#e2e8f0", font=("Segoe UI", 10, "bold"), padx=10, pady=6).grid(row=0, column=1)

            command_strip = tk.Frame(shell, bg="#edf4ff", padx=16, pady=14, highlightbackground="#bfd0e5", highlightthickness=1)
            command_strip.grid(row=1, column=0, sticky="ew", pady=(14, 0))
            command_strip.columnconfigure(0, weight=1)
            command_strip.columnconfigure(1, weight=1)
            command_strip.columnconfigure(2, weight=1)
            command_strip.columnconfigure(3, weight=1)
            command_strip.columnconfigure(4, weight=1)
            command_strip.columnconfigure(5, weight=1)
            command_strip.columnconfigure(6, weight=1)
            command_strip.columnconfigure(7, weight=1)

            self.start_button = ttk.Button(command_strip, text="Start", style="Accent.TButton", command=self.startclick)
            self.start_button.grid(row=0, column=0, sticky="ew")
            self.stop_button = ttk.Button(command_strip, text="Stop", style="Danger.TButton", command=self.stopclick, state=DISABLED)
            self.stop_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
            ttk.Button(command_strip, text="Capture Cursor", style="Secondary.TButton", command=self._capture_cursor_position).grid(row=0, column=2, sticky="ew", padx=(8, 0))
            ttk.Button(command_strip, text="Validate Plan", style="Secondary.TButton", command=self._validate_current_plan).grid(row=0, column=3, sticky="ew", padx=(8, 0))
            ttk.Checkbutton(command_strip, text="Dry Run", variable=self.dry_run_var, style="Command.TCheckbutton").grid(row=0, column=4, sticky="w", padx=(12, 0))
            ttk.Checkbutton(command_strip, text="Fail-safe", variable=self.pyautogui_failsafe_var, style="Command.TCheckbutton").grid(row=0, column=5, sticky="w", padx=(12, 0))
            ttk.Button(command_strip, text="Safety Guard", style="Secondary.TButton", command=lambda: self._set_dropdown_state("safety_guard", True)).grid(row=0, column=6, sticky="ew", padx=(8, 0))
            ttk.Button(command_strip, text="Window Settings", style="Secondary.TButton", command=self._open_settings_window).grid(row=0, column=7, sticky="ew", padx=(8, 0))
            ttk.Button(command_strip, text="Expand All", style="Secondary.TButton", command=self._expand_all_sections).grid(row=1, column=0, sticky="ew", pady=(8, 0))
            ttk.Button(command_strip, text="Collapse Extras", style="Secondary.TButton", command=self._collapse_all_sections).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
            self.command_preset_combo = ttk.Combobox(command_strip, textvariable=self.behaviour_preset_var, values=("Balanced", "Precision", "Burst Sprint", "Human Mimic"), state="readonly")
            self.command_preset_combo.grid(row=1, column=2, columnspan=2, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="Apply Preset", style="Secondary.TButton", command=self._apply_behaviour_preset).grid(row=1, column=4, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="Health Check", style="Secondary.TButton", command=self._open_health_dashboard).grid(row=1, column=5, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="Session Report", style="Secondary.TButton", command=self._export_session_report).grid(row=1, column=6, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="State Folder", style="Secondary.TButton", command=self._open_state_folder).grid(row=1, column=7, sticky="ew", padx=(8, 0), pady=(8, 0))
            tk.Label(command_strip, textvariable=self.safety_status_var, bg="#edf4ff", fg="#334155", font=("Segoe UI", 9, "bold"), wraplength=1030, justify=LEFT).grid(row=2, column=0, columnspan=8, sticky="w", pady=(10, 0))
            tk.Label(command_strip, textvariable=self.preset_summary_var, bg="#edf4ff", fg="#0f766e", font=("Segoe UI", 9, "bold"), wraplength=1030, justify=LEFT).grid(row=3, column=0, columnspan=8, sticky="w", pady=(4, 0))

            workspace = tk.Frame(shell, bg="#dbe7f2")
            workspace.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
            workspace.columnconfigure(0, weight=3)
            workspace.columnconfigure(1, weight=2)

            left_stack = tk.Frame(workspace, bg="#dbe7f2")
            left_stack.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
            left_stack.columnconfigure(0, weight=1)

            right_stack = tk.Frame(workspace, bg="#dbe7f2")
            right_stack.grid(row=0, column=1, sticky="nsew")
            right_stack.columnconfigure(0, weight=1)

            quick_card, quick_body = self._create_dropdown_section(
                left_stack,
                "quick_start",
                "Quick Start",
                "Keep the most common fields open and tuck the rest away until you need them.",
                start_open=True,
            )
            quick_card.grid(row=0, column=0, sticky="ew")
            quick_body.columnconfigure(1, weight=1)
            quick_body.columnconfigure(3, weight=1)

            tk.Label(quick_body, text="Target X", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(quick_body, textvariable=self.target_x_var, width=16).grid(row=0, column=1, sticky="ew", pady=(0, 6))
            tk.Label(quick_body, text="Target Y", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(quick_body, textvariable=self.target_y_var, width=16).grid(row=0, column=3, sticky="ew", pady=(0, 6))

            ttk.Button(quick_body, text="Use Current Cursor", style="Secondary.TButton", command=self._capture_cursor_position).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            ttk.Button(quick_body, text="Swap X / Y", style="Secondary.TButton", command=self._swap_coordinates).grid(row=1, column=2, columnspan=2, sticky="ew", padx=(14, 0), pady=(0, 8))

            tk.Label(quick_body, text="Click type", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
            self.click_type_combo = ttk.Combobox(quick_body, textvariable=self.click_mode_var, values=tuple(self.CLICK_TYPES.keys()), state="readonly")
            self.click_type_combo.grid(row=2, column=1, sticky="ew", pady=(0, 6))
            tk.Label(quick_body, text="Repeat mode", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            self.repeat_mode_combo = ttk.Combobox(quick_body, textvariable=self.repeat_mode_var, values=("Infinite", "Burst Count"), state="readonly")
            self.repeat_mode_combo.grid(row=2, column=3, sticky="ew", pady=(0, 6))

            tk.Label(quick_body, text="Burst count", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 6))
            self.repeat_count_entry = ttk.Entry(quick_body, textvariable=self.repeat_count_var)
            self.repeat_count_entry.grid(row=3, column=1, sticky="ew", pady=(0, 6))
            tk.Label(quick_body, text="Stop hotkey", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=3, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(quick_body, textvariable=self.stop_hotkey_var).grid(row=3, column=3, sticky="ew", pady=(0, 6))

            timing_card, timing_body = self._create_dropdown_section(
                left_stack,
                "timing",
                "Timing and Repeat",
                "Delay, countdown, runtime cap, and other rhythm controls live here.",
            )
            timing_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
            timing_body.columnconfigure(1, weight=1)
            timing_body.columnconfigure(3, weight=1)

            tk.Label(timing_body, text="Delay (seconds)", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(timing_body, textvariable=self.delay_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
            tk.Label(timing_body, text="Delay variance", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(timing_body, textvariable=self.delay_variance_var).grid(row=0, column=3, sticky="ew", pady=(0, 6))

            tk.Label(timing_body, text="Countdown (sec)", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(timing_body, textvariable=self.countdown_var).grid(row=1, column=1, sticky="ew", pady=(0, 6))
            tk.Label(timing_body, text="Runtime cap (sec)", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=1, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(timing_body, textvariable=self.runtime_limit_var).grid(row=1, column=3, sticky="ew", pady=(0, 6))

            tk.Label(timing_body, text="Delay presets", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
            preset_bar = tk.Frame(timing_body, bg="#f8fafc")
            preset_bar.grid(row=2, column=1, columnspan=3, sticky="w", pady=(0, 6))
            for index, preset in enumerate(self.DELAY_PRESETS):
                ttk.Button(preset_bar, text=preset, style="Chip.TButton", command=lambda value=preset: self._set_delay_preset(value)).grid(row=0, column=index, padx=(0 if index == 0 else 4, 0))

            safety_card, safety_body = self._create_dropdown_section(
                left_stack,
                "safety_guard",
                "Safety Guard",
                "Action caps, corner fail-safe behaviour, and plan validation.",
            )
            safety_card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
            safety_body.columnconfigure(1, weight=1)
            safety_body.columnconfigure(3, weight=1)

            tk.Label(safety_body, text="Max actions cap", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(safety_body, textvariable=self.max_actions_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
            ttk.Checkbutton(safety_body, text="PyAutoGUI corner fail-safe", variable=self.pyautogui_failsafe_var, style="App.TCheckbutton").grid(row=0, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Checkbutton(safety_body, text="Dry run, no click output", variable=self.dry_run_var, style="App.TCheckbutton").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))
            tk.Label(safety_body, text="Safety presets", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
            safety_preset_row = tk.Frame(safety_body, bg="#f8fafc")
            safety_preset_row.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(14, 0), pady=(0, 6))
            for index, preset_name in enumerate(SAFETY_PRESETS):
                safety_preset_row.columnconfigure(index, weight=1)
                ttk.Button(safety_preset_row, text=preset_name, style="Chip.TButton", command=lambda value=preset_name: self._apply_safety_preset(value)).grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0))
            ttk.Button(safety_body, text="Validate Plan", style="Secondary.TButton", command=self._validate_current_plan).grid(row=3, column=0, sticky="ew", pady=(0, 6))
            tk.Label(safety_body, textvariable=self.run_intelligence_var, bg="#f8fafc", fg="#475569", font=("Segoe UI", 9), wraplength=620, justify=LEFT).grid(row=3, column=1, columnspan=3, sticky="w", padx=(14, 0), pady=(0, 6))

            innovation_card, innovation_body = self._create_dropdown_section(
                left_stack,
                "innovation",
                "Innovation Lab",
                "Preset behaviours, jitter shaping, and fatigue-friendly pacing options.",
            )
            innovation_card.grid(row=3, column=0, sticky="ew", pady=(12, 0))
            innovation_body.columnconfigure(1, weight=1)
            innovation_body.columnconfigure(3, weight=1)

            tk.Label(innovation_body, text="Behaviour preset", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            self.innovation_preset_combo = ttk.Combobox(innovation_body, textvariable=self.behaviour_preset_var, values=("Balanced", "Precision", "Burst Sprint", "Human Mimic"), state="readonly")
            self.innovation_preset_combo.grid(row=0, column=1, sticky="ew", pady=(0, 6))
            ttk.Button(innovation_body, text="Apply", style="Secondary.TButton", command=self._apply_behaviour_preset).grid(row=0, column=2, sticky="ew", padx=(14, 0), pady=(0, 6))
            ttk.Button(innovation_body, text="Open Window Studio", style="Secondary.TButton", command=lambda: self._set_dropdown_state("window_studio", True)).grid(row=0, column=3, sticky="ew", pady=(0, 6))

            tk.Label(innovation_body, textvariable=self.preset_summary_var, bg="#f8fafc", fg="#0f766e", font=("Segoe UI", 9, "bold"), wraplength=620, justify=LEFT).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))

            tk.Label(innovation_body, text="X jitter", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(innovation_body, textvariable=self.jitter_x_var).grid(row=2, column=1, sticky="ew", pady=(0, 6))
            tk.Label(innovation_body, text="Y jitter", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(innovation_body, textvariable=self.jitter_y_var).grid(row=2, column=3, sticky="ew", pady=(0, 6))

            tk.Label(innovation_body, text="Micro-pause every", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(innovation_body, textvariable=self.micro_pause_every_var).grid(row=3, column=1, sticky="ew", pady=(0, 6))
            tk.Label(innovation_body, text="Micro-pause sec", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=3, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(innovation_body, textvariable=self.micro_pause_duration_var).grid(row=3, column=3, sticky="ew", pady=(0, 6))

            innovation_flags = tk.Frame(innovation_body, bg="#f8fafc")
            innovation_flags.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(6, 0))
            ttk.Checkbutton(innovation_flags, text="Human-like clicks", variable=self.human_like_var, style="App.TCheckbutton").grid(row=0, column=0, sticky="w")
            ttk.Checkbutton(innovation_flags, text="Play sound on finish", variable=self.play_sound_var, style="App.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(18, 0))
            ttk.Checkbutton(innovation_flags, text="Minimize while clicking", variable=self.minimize_on_start_var, style="App.TCheckbutton").grid(row=0, column=2, sticky="w", padx=(18, 0))
            ttk.Checkbutton(innovation_flags, text="Restore after run", variable=self.restore_after_run_var, style="App.TCheckbutton").grid(row=0, column=3, sticky="w", padx=(18, 0))

            tools_card, tools_body = self._create_dropdown_section(
                left_stack,
                "tools",
                "Tools and Helpers",
                "Open specialist windows only when you need them instead of keeping everything on screen.",
            )
            tools_card.grid(row=4, column=0, sticky="ew", pady=(12, 0))
            tools_body.columnconfigure(0, weight=1)
            tools_body.columnconfigure(1, weight=1)

            ttk.Button(tools_body, text="Find Coordinates", style="Secondary.TButton", command=self._open_finder).grid(row=0, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(tools_body, text="Coordinate Sequence", style="Secondary.TButton", command=self._open_sequence_builder).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(tools_body, text="Advanced Colour Clicker", style="Secondary.TButton", command=Colour_Clicker).grid(row=1, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(tools_body, text="Locate and Click", style="Secondary.TButton", command=Locate_Click).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(tools_body, text="Photo Clicker", style="Secondary.TButton", command=Photo_Clicker).grid(row=2, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(tools_body, text="Mega Spam", style="Secondary.TButton", command=self._open_mega_spam).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(tools_body, text="Record Toggle", style="Secondary.TButton", command=self._toggle_recording).grid(row=3, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(tools_body, text="Recording Studio", style="Secondary.TButton", command=self._open_recording_studio).grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(tools_body, text="Playback", style="Secondary.TButton", command=self._play_recording).grid(row=4, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(tools_body, text="Health Check", style="Secondary.TButton", command=self._open_health_dashboard).grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(tools_body, text="Feedback", style="Secondary.TButton", command=feedback).grid(row=5, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(tools_body, text="About Page", style="Secondary.TButton", command=self._open_about_page).grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(tools_body, text="GitHub", style="Secondary.TButton", command=self._open_github_page).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 12))
            tk.Label(tools_body, textvariable=self.recording_summary_var, bg="#f8fafc", fg="#0f766e", font=("Segoe UI", 9, "bold"), wraplength=620, justify=LEFT).grid(row=7, column=0, columnspan=2, sticky="w")

            profiles_card, profiles_body = self._create_dropdown_section(
                left_stack,
                "profiles",
                "Profiles and Recall",
                "Save and reload working setups without keeping the controls visible all the time.",
            )
            profiles_card.grid(row=5, column=0, sticky="ew", pady=(12, 0))
            profiles_body.columnconfigure(0, weight=1)
            profiles_body.columnconfigure(1, weight=1)

            tk.Label(profiles_body, text="Profile name", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
            ttk.Entry(profiles_body, textvariable=self.profile_name_var).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
            tk.Label(profiles_body, text="Saved profiles", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 6))
            self.profile_combo = ttk.Combobox(profiles_body, textvariable=self.profile_choice_var, state="readonly")
            self.profile_combo.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            ttk.Button(profiles_body, text="Save / Update", style="Secondary.TButton", command=self._save_current_profile).grid(row=4, column=0, sticky="ew")
            ttk.Button(profiles_body, text="Load", style="Secondary.TButton", command=self._load_selected_profile).grid(row=4, column=1, sticky="ew", padx=(8, 0))
            ttk.Button(profiles_body, text="Delete Profile", style="Secondary.TButton", command=self._delete_selected_profile).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            ttk.Button(profiles_body, text="Export Profiles", style="Secondary.TButton", command=self._export_profiles).grid(row=6, column=0, sticky="ew", pady=(8, 0))
            ttk.Button(profiles_body, text="Import Profiles", style="Secondary.TButton", command=self._import_profiles).grid(row=6, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))

            window_card, window_body = self._create_dropdown_section(
                left_stack,
                "window_studio",
                "Window Studio",
                "Desktop-focused options, visual tuning, and layout presets stay concealed until needed.",
            )
            window_card.grid(row=6, column=0, sticky="ew", pady=(12, 0))
            window_body.columnconfigure(1, weight=1)

            tk.Label(window_body, text="Theme", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            self.theme_combo_main = ttk.Combobox(window_body, textvariable=self.theme_var, values=("Light", "Dark", "Ocean"), state="readonly")
            self.theme_combo_main.grid(row=0, column=1, sticky="ew", pady=(0, 6))
            tk.Label(window_body, text="Window opacity", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 6))
            ttk.Scale(window_body, variable=self.window_opacity_var, from_=0.70, to=1.00, style="App.Horizontal.TScale", command=lambda _value: self._apply_window_preferences()).grid(row=1, column=1, sticky="ew", pady=(0, 6))
            tk.Label(window_body, text="UI scale", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
            ttk.Scale(window_body, variable=self.ui_scale_var, from_=0.90, to=1.35, style="App.Horizontal.TScale", command=lambda _value: self._apply_window_preferences()).grid(row=2, column=1, sticky="ew", pady=(0, 6))

            window_toggle_a = tk.Frame(window_body, bg="#f8fafc")
            window_toggle_a.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
            ttk.Checkbutton(window_toggle_a, text="Keep window on top", variable=self.topmost_var, style="App.TCheckbutton").grid(row=0, column=0, sticky="w")
            ttk.Checkbutton(window_toggle_a, text="Close button goes to tray", variable=self.close_to_tray_var, style="App.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(18, 0))

            window_toggle_b = tk.Frame(window_body, bg="#f8fafc")
            window_toggle_b.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))
            ttk.Checkbutton(window_toggle_b, text="Remember size and position", variable=self.remember_window_geometry_var, style="App.TCheckbutton").grid(row=0, column=0, sticky="w")
            ttk.Checkbutton(window_toggle_b, text="Fullscreen mode", variable=self.fullscreen_var, style="App.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(18, 0))

            preset_row = tk.Frame(window_body, bg="#f8fafc")
            preset_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            preset_row.columnconfigure(0, weight=1)
            preset_row.columnconfigure(1, weight=1)
            preset_row.columnconfigure(2, weight=1)
            ttk.Button(preset_row, text="Compact", style="Secondary.TButton", command=lambda: self._set_window_size_preset(920, 640)).grid(row=0, column=0, sticky="ew")
            ttk.Button(preset_row, text="Wide", style="Secondary.TButton", command=lambda: self._set_window_size_preset(1180, 760)).grid(row=0, column=1, sticky="ew", padx=8)
            ttk.Button(preset_row, text="Studio", style="Secondary.TButton", command=lambda: self._set_window_size_preset(1360, 860)).grid(row=0, column=2, sticky="ew")

            action_row = tk.Frame(window_body, bg="#f8fafc")
            action_row.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            action_row.columnconfigure(0, weight=1)
            action_row.columnconfigure(1, weight=1)
            ttk.Button(action_row, text="Center Window", style="Secondary.TButton", command=self._center_window).grid(row=0, column=0, sticky="ew")
            ttk.Button(action_row, text="Reset Layout", style="Secondary.TButton", command=self._reset_window_layout).grid(row=0, column=1, sticky="ew", padx=(8, 0))

            ttk.Button(window_body, text="More Window Controls", style="Secondary.TButton", command=self._open_settings_window).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 8))
            tk.Label(window_body, textvariable=self.window_summary_var, bg="#f8fafc", fg="#0f766e", font=("Segoe UI", 9, "bold"), wraplength=620, justify=LEFT).grid(row=8, column=0, columnspan=2, sticky="w")

            summary_card, summary_body = self._create_card(
                right_stack,
                "Live Review",
                "The right rail stays visible while the deeper dropdown sections stay closed."
            )
            summary_card.grid(row=0, column=0, sticky="ew")
            tk.Label(summary_body, text="Plan", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(summary_body, textvariable=self.plan_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 10), wraplength=360, justify=LEFT).grid(row=1, column=0, sticky="w", pady=(4, 8))
            tk.Label(summary_body, text="Run Intelligence", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w")
            tk.Label(summary_body, textvariable=self.run_intelligence_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 10), wraplength=360, justify=LEFT).grid(row=3, column=0, sticky="w", pady=(4, 8))
            tk.Label(summary_body, text="Readiness", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w")
            tk.Label(summary_body, textvariable=self.readiness_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 9), wraplength=360, justify=LEFT).grid(row=5, column=0, sticky="w", pady=(4, 8))
            tk.Label(summary_body, text="Profile", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=6, column=0, sticky="w")
            tk.Label(summary_body, textvariable=self.profile_state_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 9), wraplength=360, justify=LEFT).grid(row=7, column=0, sticky="w", pady=(4, 8))
            tk.Label(summary_body, text="Safety", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=8, column=0, sticky="w")
            tk.Label(summary_body, textvariable=self.safety_status_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 10), wraplength=360, justify=LEFT).grid(row=9, column=0, sticky="w", pady=(4, 8))
            tk.Label(summary_body, text="Session", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=10, column=0, sticky="w")
            tk.Label(summary_body, textvariable=self.session_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 10), wraplength=360, justify=LEFT).grid(row=11, column=0, sticky="w", pady=(4, 8))
            tk.Label(summary_body, text="Last run", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=12, column=0, sticky="w")
            tk.Label(summary_body, textvariable=self.last_run_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 10), wraplength=360, justify=LEFT).grid(row=13, column=0, sticky="w", pady=(4, 8))
            self.total_session_clicks_var = tk.StringVar(value="Total Session Clicks: 0")
            self.session_elapsed_var = tk.StringVar(value="Session Elapsed: 00:00:00")
            tk.Label(summary_body, textvariable=self.total_session_clicks_var, bg="#f8fafc", fg="#0f766e", font=("Segoe UI", 9, "bold")).grid(row=14, column=0, sticky="w")
            tk.Label(summary_body, textvariable=self.session_elapsed_var, bg="#f8fafc", fg="#0f766e", font=("Segoe UI", 9, "bold")).grid(row=15, column=0, sticky="w", pady=(4, 0))
            tk.Label(summary_body, text="Preset", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=16, column=0, sticky="w", pady=(12, 0))
            tk.Label(summary_body, textvariable=self.preset_summary_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 10), wraplength=360, justify=LEFT).grid(row=17, column=0, sticky="w", pady=(4, 0))

            support_card, support_body = self._create_card(
                right_stack,
                "Support Hub",
                "State, health, and export shortcuts stay close to the live run summary."
            )
            support_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
            support_body.columnconfigure(0, weight=1)
            support_body.columnconfigure(1, weight=1)
            ttk.Button(support_body, text="Health Check", style="Secondary.TButton", command=self._open_health_dashboard).grid(row=0, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(support_body, text="Session Report", style="Secondary.TButton", command=self._export_session_report).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(support_body, text="Support Bundle", style="Secondary.TButton", command=self._create_support_bundle).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            ttk.Button(support_body, text="Backup State", style="Secondary.TButton", command=self._backup_state_snapshot).grid(row=2, column=0, sticky="ew")
            ttk.Button(support_body, text="Open State Folder", style="Secondary.TButton", command=self._open_state_folder).grid(row=2, column=1, sticky="ew", padx=(8, 0))

            controls_card, controls_body = self._create_card(
                right_stack,
                "Controls and Activity",
                "Always-available side rail for launch actions and recent activity."
            )
            controls_card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
            controls_body.columnconfigure(0, weight=1)
            controls_body.rowconfigure(4, weight=1)
            ttk.Button(controls_body, text="Mini Control", style="Secondary.TButton", command=self._open_mini_control).grid(row=0, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(controls_body, text="Old Style GUI", style="Secondary.TButton", command=self._open_old_window).grid(row=1, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(controls_body, text="Recording Studio", style="Secondary.TButton", command=self._open_recording_studio).grid(row=2, column=0, sticky="ew", pady=(0, 8))
            tk.Label(controls_body, text="Recent activity", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(4, 6))
            self.activity_list = Listbox(controls_body, height=10, font=("Segoe UI", 9), bg="white", fg="#0f172a", selectbackground="#1d4ed8", activestyle="none", exportselection=False)
            self.activity_list.grid(row=4, column=0, sticky="nsew", pady=(0, 8))
            ttk.Button(controls_body, text="Exit", style="Secondary.TButton", command=self.EXITME).grid(row=5, column=0, sticky="ew")

            footer = tk.Frame(shell, bg="#dbe7f2")
            footer.grid(row=3, column=0, sticky="ew", pady=(16, 0))
            footer.columnconfigure(0, weight=1)

            status_strip = tk.Frame(footer, bg="#0f172a", padx=16, pady=12)
            status_strip.grid(row=0, column=0, sticky="ew")
            tk.Label(status_strip, text="Status", bg="#0f172a", fg="#f8fafc", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(status_strip, textvariable=self.status_var, bg="#0f172a", fg="#cbd5e1", font=("Segoe UI", 10), justify=LEFT, wraplength=1080).grid(row=1, column=0, sticky="w", pady=(4, 0))

            for variable in (
                self.target_x_var,
                self.target_y_var,
                self.click_mode_var,
                self.delay_var,
                self.delay_variance_var,
                self.jitter_x_var,
                self.jitter_y_var,
                self.countdown_var,
                self.runtime_limit_var,
                self.max_actions_var,
                self.stop_hotkey_var,
                self.repeat_mode_var,
                self.repeat_count_var,
                self.behaviour_preset_var,
                self.micro_pause_every_var,
                self.micro_pause_duration_var,
                self.theme_var,
                self.profile_name_var,
                self.profile_choice_var,
            ):
                variable.trace_add("write", self._handle_state_change)
            for variable in (
                self.topmost_var,
                self.minimize_on_start_var,
                self.restore_after_run_var,
                self.close_to_tray_var,
                self.fullscreen_var,
                self.remember_window_geometry_var,
                self.window_opacity_var,
                self.ui_scale_var,
            ):
                variable.trace_add("write", self._handle_window_settings_change)
            for variable in (
                self.human_like_var,
                self.play_sound_var,
                self.dry_run_var,
                self.pyautogui_failsafe_var,
            ):
                variable.trace_add("write", self._handle_state_change)

            self.repeat_mode_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_repeat_state())
            self.profile_combo.bind("<<ComboboxSelected>>", self._sync_profile_name_from_choice)
            self.theme_combo_main.bind("<<ComboboxSelected>>", lambda _event: self._apply_theme())
            self.command_preset_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_preset_summary())
            self.innovation_preset_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_preset_summary())

            self._refresh_preset_summary()
            self._refresh_window_summary()
            self._collapse_all_sections()
            self.after_idle(self._update_main_scroll_region)

        def _build_menu(self):
            menu = Menu(self)

            tools_menu = Menu(menu, tearoff=0)
            tools_menu.add_command(label='Start', command=self.startclick)
            tools_menu.add_command(label='Stop', command=self.stopclick)
            tools_menu.add_separator()
            tools_menu.add_command(label='Find Coordinates', command=self._open_finder)
            tools_menu.add_command(label='Coordinate Sequence', command=self._open_sequence_builder)
            tools_menu.add_command(label='Advanced Colour Clicker', command=Colour_Clicker)
            tools_menu.add_command(label='Locate and Click', command=Locate_Click)
            tools_menu.add_command(label='Photo Clicker', command=Photo_Clicker)
            tools_menu.add_command(label='Auto Clicker Mega Spam', command=self._open_mega_spam)
            tools_menu.add_command(label='Recording Studio', command=self._open_recording_studio)
            tools_menu.add_command(label='Health Check', command=self._open_health_dashboard)
            tools_menu.add_command(label='Export Session Report', command=self._export_session_report)
            tools_menu.add_command(label='Create Support Bundle', command=self._create_support_bundle)
            tools_menu.add_command(label='Backup State Snapshot', command=self._backup_state_snapshot)
            tools_menu.add_command(label='Open State Folder', command=self._open_state_folder)
            tools_menu.add_separator()
            tools_menu.add_command(label='Window Settings', command=self._open_settings_window)
            tools_menu.add_command(label='Old Style GUI', command=self._open_old_window)
            tools_menu.add_command(label='Exit', command=self.EXITME)
            menu.add_cascade(label='Tools', menu=tools_menu)

            help_menu = Menu(menu, tearoff=0)
            help_menu.add_command(label='About Page', command=self._open_about_page)
            help_menu.add_command(label='GitHub Page', command=self._open_github_page)
            help_menu.add_command(label='Tutorial', command=tutorial)
            help_menu.add_command(label='Contact', command=self._open_contact_page)
            help_menu.add_command(label='Version Number', command=NOTIFICATION)
            help_menu.add_command(label='Send Feedback', command=feedback)
            menu.add_cascade(label='Help', menu=help_menu)

            self.config(menu=menu)

        def _build_context_menu(self):
            self.popup = Menu(self, tearoff=0)
            self.popup.add_command(label='Capture Current Cursor', command=self._capture_cursor_position)
            self.popup.add_command(label='Start', command=self.startclick)
            self.popup.add_command(label='Stop', command=self.stopclick)
            self.popup.add_separator()
            self.popup.add_command(label='Coordinate Sequence', command=self._open_sequence_builder)
            self.popup.add_command(label='Advanced Colour Clicker', command=Colour_Clicker)
            self.popup.add_command(label='Find Coordinates', command=self._open_finder)
            self.popup.add_command(label='Locate and Click', command=Locate_Click)
            self.popup.add_command(label='Photo Clicker', command=Photo_Clicker)
            self.popup.add_command(label='Recording Studio', command=self._open_recording_studio)
            self.popup.add_command(label='Health Check', command=self._open_health_dashboard)
            self.popup.add_command(label='Export Session Report', command=self._export_session_report)
            self.popup.add_command(label='Create Support Bundle', command=self._create_support_bundle)
            self.popup.add_command(label='Backup State Snapshot', command=self._backup_state_snapshot)
            self.popup.add_command(label='Open State Folder', command=self._open_state_folder)
            self.popup.add_separator()
            self.popup.add_command(label='Window Settings', command=self._open_settings_window)
            self.popup.add_command(label='Exit', command=self.EXITME)

        def _show_context_menu(self, event):
            try:
                self.popup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                self.popup.grab_release()

        def _handle_main_canvas_configure(self, event=None):
            if not hasattr(self, "main_canvas") or not hasattr(self, "main_canvas_window"):
                return

            canvas_width = self.main_canvas.winfo_width() if event is None else event.width
            target_width = max(canvas_width - 2, self.main_shell_min_width)
            self.main_canvas.itemconfigure(self.main_canvas_window, width=target_width)
            self._update_main_scroll_region()

        def _update_main_scroll_region(self, _event=None):
            if hasattr(self, "main_canvas") and self.main_canvas.winfo_exists():
                self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

        def _bind_main_scroll_support(self):
            self.bind_all("<MouseWheel>", self._on_main_mousewheel)

        def _on_main_mousewheel(self, event):
            if not hasattr(self, "main_canvas") or not self.main_canvas.winfo_exists():
                return
            pointer_widget = self.winfo_containing(event.x_root, event.y_root)
            while pointer_widget is not None:
                if pointer_widget in (self.main_canvas, self.scroll_frame):
                    break
                pointer_widget = pointer_widget.master
            else:
                return

            if event.delta == 0:
                return

            step = -1 if event.delta > 0 else 1
            if event.state & 0x1:
                self.main_canvas.xview_scroll(step, "units")
            else:
                self.main_canvas.yview_scroll(step, "units")

        def _normalize_window_opacity(self):
            try:
                opacity = float(self.window_opacity_var.get())
            except Exception:
                opacity = 1.0
            return max(0.70, min(1.00, opacity))

        def _normalize_ui_scale(self):
            try:
                scale = float(self.ui_scale_var.get())
            except Exception:
                scale = 1.0
            return max(0.90, min(1.35, scale))

        def _refresh_window_summary(self):
            close_action = "tray" if self.close_to_tray_var.get() else "exit"
            geometry_mode = "remembered" if self.remember_window_geometry_var.get() else "temporary"
            self.window_summary_var.set(
                f"{self.theme_var.get()} theme | {int(self._normalize_window_opacity() * 100)}% opacity | "
                f"{int(self._normalize_ui_scale() * 100)}% UI scale | close button -> {close_action} | "
                f"fullscreen {'on' if self.fullscreen_var.get() else 'off'} | geometry {geometry_mode}."
            )

        def _handle_window_settings_change(self, *_args):
            self._apply_window_preferences()
            self._schedule_workspace_save()

        def _handle_close_request(self):
            if self.close_to_tray_var.get():
                self._minimize_to_tray()
            else:
                self.EXITME()

        def _set_window_size_preset(self, width, height):
            self.fullscreen_var.set(False)
            self.geometry(f"{width}x{height}")
            self._center_window()
            self.status_var.set(f"Window resized to {width} x {height}.")
            self._append_activity(f"Window preset applied: {width} x {height}.")

        def _center_window(self):
            try:
                self.update_idletasks()
                width = self.winfo_width()
                height = self.winfo_height()
                x_pos = max(0, (self.screen_width - width) // 2)
                y_pos = max(0, (self.screen_height - height) // 2)
                self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
                self._append_activity("Window centered on screen.")
            except Exception:
                pass

        def _reset_window_layout(self):
            self.fullscreen_var.set(False)
            self.window_opacity_var.set(1.0)
            self.ui_scale_var.set(1.0)
            self._set_window_size_preset(1080, 760)
            self.status_var.set("Window layout reset to the default studio preset.")

        def _fit_window_to_screen(self):
            self.fullscreen_var.set(False)
            width = max(860, min(self.screen_width - 80, 1480))
            height = max(560, min(self.screen_height - 120, 920))
            x_pos = max(0, (self.screen_width - width) // 2)
            y_pos = max(0, (self.screen_height - height) // 2)
            self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
            self.status_var.set(f"Window fit to screen at {width} x {height}.")
            self._append_activity(f"Window fit to screen at {width} x {height}.")
            self._schedule_workspace_save()

        def _set_window_opacity_preset(self, value):
            self.window_opacity_var.set(value)
            self._apply_window_preferences()
            self._schedule_workspace_save()

        def _set_ui_scale_preset(self, value):
            self.ui_scale_var.set(value)
            self._apply_window_preferences()
            self._schedule_workspace_save()

        def _remember_current_window_layout(self):
            self.remember_window_geometry_var.set(True)
            self._persist_workspace_state()
            self.status_var.set("Current window layout saved.")
            self._append_activity("Current window layout saved.")

        def _reset_visual_preferences(self):
            self.theme_var.set("Light")
            self.window_opacity_var.set(1.0)
            self.ui_scale_var.set(1.0)
            self._apply_theme()
            self._apply_window_preferences()
            self.status_var.set("Visual preferences reset.")
            self._append_activity("Visual preferences reset.")

        def _apply_window_preferences(self):
            opacity = round(self._normalize_window_opacity(), 2)
            scale = round(self._normalize_ui_scale(), 2)

            try:
                if abs(float(self.window_opacity_var.get()) - opacity) > 0.001:
                    self.window_opacity_var.set(opacity)
            except Exception:
                self.window_opacity_var.set(opacity)

            try:
                if abs(float(self.ui_scale_var.get()) - scale) > 0.001:
                    self.ui_scale_var.set(scale)
            except Exception:
                self.ui_scale_var.set(scale)

            try:
                self.attributes("-topmost", self.topmost_var.get())
            except Exception:
                pass
            try:
                self.attributes("-alpha", opacity)
            except Exception:
                pass
            try:
                self.attributes("-fullscreen", self.fullscreen_var.get())
            except Exception:
                pass
            try:
                self.tk.call("tk", "scaling", self.base_tk_scaling * scale)
            except Exception:
                pass

            self.protocol("WM_DELETE_WINDOW", self._handle_close_request)
            self._refresh_window_summary()
            self.after_idle(self._handle_main_canvas_configure)

        def _open_about_page(self):
            webbrowser.open_new(r"https://kai9987kai.github.io/AutoClicker.html")

        def _open_github_page(self):
            webbrowser.open_new(r"https://github.com/kai9987kai/AutoClicker")

        def _open_contact_page(self):
            Contact_Page()

        def _open_mega_spam(self):
            Mega_Spam()

        def _open_finder(self):
            Coordinates_Finder()

        def _restart_program(self):
            python = sys.executable
            os.execl(python, python, *sys.argv)

        def _open_old_window(self):
            self.destroy()
            OldStyleGUI()

        def _set_delay_preset(self, value):
            self.delay_var.set(value)

        def _sync_profile_name_from_choice(self, _event=None):
            if self.profile_choice_var.get().strip():
                self.profile_name_var.set(self.profile_choice_var.get().strip())

        def _collect_profile_data(self):
            return {
                "target_x": self.target_x_var.get(),
                "target_y": self.target_y_var.get(),
                "click_mode": self.click_mode_var.get(),
                "delay": self.delay_var.get(),
                "delay_variance": self.delay_variance_var.get(),
                "jitter_x": self.jitter_x_var.get(),
                "jitter_y": self.jitter_y_var.get(),
                "countdown": self.countdown_var.get(),
                "runtime_limit": self.runtime_limit_var.get(),
                "max_actions": self.max_actions_var.get(),
                "stop_hotkey": self.stop_hotkey_var.get(),
                "repeat_mode": self.repeat_mode_var.get(),
                "repeat_count": self.repeat_count_var.get(),
                "behaviour_preset": self.behaviour_preset_var.get(),
                "micro_pause_every": self.micro_pause_every_var.get(),
                "micro_pause_duration": self.micro_pause_duration_var.get(),
                "topmost": self.topmost_var.get(),
                "minimize_on_start": self.minimize_on_start_var.get(),
                "restore_after_run": self.restore_after_run_var.get(),
                "close_to_tray": self.close_to_tray_var.get(),
                "fullscreen": self.fullscreen_var.get(),
                "remember_window_geometry": self.remember_window_geometry_var.get(),
                "window_opacity": self._normalize_window_opacity(),
                "ui_scale": self._normalize_ui_scale(),
                "human_like": self.human_like_var.get(),
                "play_sound": self.play_sound_var.get(),
                "dry_run": self.dry_run_var.get(),
                "pyautogui_failsafe": self.pyautogui_failsafe_var.get(),
                "theme": self.theme_var.get(),
            }

        def _apply_profile_data(self, profile_data):
            self.target_x_var.set(str(profile_data.get("target_x", self.target_x_var.get())))
            self.target_y_var.set(str(profile_data.get("target_y", self.target_y_var.get())))
            self.click_mode_var.set(profile_data.get("click_mode", self.click_mode_var.get()))
            self.delay_var.set(str(profile_data.get("delay", self.delay_var.get())))
            self.delay_variance_var.set(str(profile_data.get("delay_variance", self.delay_variance_var.get())))
            self.jitter_x_var.set(str(profile_data.get("jitter_x", self.jitter_x_var.get())))
            self.jitter_y_var.set(str(profile_data.get("jitter_y", self.jitter_y_var.get())))
            self.countdown_var.set(str(profile_data.get("countdown", self.countdown_var.get())))
            self.runtime_limit_var.set(str(profile_data.get("runtime_limit", self.runtime_limit_var.get())))
            self.max_actions_var.set(str(profile_data.get("max_actions", self.max_actions_var.get())))
            self.stop_hotkey_var.set(str(profile_data.get("stop_hotkey", self.stop_hotkey_var.get())))
            self.repeat_mode_var.set(profile_data.get("repeat_mode", self.repeat_mode_var.get()))
            self.repeat_count_var.set(str(profile_data.get("repeat_count", self.repeat_count_var.get())))
            self.behaviour_preset_var.set(profile_data.get("behaviour_preset", self.behaviour_preset_var.get()))
            self.micro_pause_every_var.set(str(profile_data.get("micro_pause_every", self.micro_pause_every_var.get())))
            self.micro_pause_duration_var.set(str(profile_data.get("micro_pause_duration", self.micro_pause_duration_var.get())))
            self.topmost_var.set(bool(profile_data.get("topmost", self.topmost_var.get())))
            self.minimize_on_start_var.set(bool(profile_data.get("minimize_on_start", self.minimize_on_start_var.get())))
            self.restore_after_run_var.set(bool(profile_data.get("restore_after_run", self.restore_after_run_var.get())))
            self.close_to_tray_var.set(bool(profile_data.get("close_to_tray", self.close_to_tray_var.get())))
            self.fullscreen_var.set(bool(profile_data.get("fullscreen", self.fullscreen_var.get())))
            self.remember_window_geometry_var.set(bool(profile_data.get("remember_window_geometry", self.remember_window_geometry_var.get())))
            self.window_opacity_var.set(float(profile_data.get("window_opacity", self.window_opacity_var.get())))
            self.ui_scale_var.set(float(profile_data.get("ui_scale", self.ui_scale_var.get())))
            self.human_like_var.set(bool(profile_data.get("human_like", self.human_like_var.get())))
            self.play_sound_var.set(bool(profile_data.get("play_sound", self.play_sound_var.get())))
            self.dry_run_var.set(bool(profile_data.get("dry_run", self.dry_run_var.get())))
            self.pyautogui_failsafe_var.set(bool(profile_data.get("pyautogui_failsafe", self.pyautogui_failsafe_var.get())))
            self.theme_var.set(profile_data.get("theme", self.theme_var.get()))
            self._refresh_preset_summary()
            self._apply_theme()
            self._apply_window_preferences()
            self._update_repeat_state()
            self._update_plan_summary()

        def _write_profiles_to_disk(self):
            _atomic_write_json(self.profile_file, self.saved_profiles, sort_keys=True)

        def _set_status_safe(self, message):
            if threading.current_thread() is threading.main_thread():
                self.status_var.set(message)
            else:
                try:
                    self.after(0, lambda value=message: self.status_var.set(value))
                except:
                    pass

        def _append_activity(self, message):
            if threading.current_thread() is not threading.main_thread():
                try:
                    self.after(0, lambda value=message: self._append_activity(value))
                except:
                    pass
                return

            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            entry = f"{timestamp}  {message}"
            self.activity_history.append(entry)
            self.activity_history = self.activity_history[-80:]
            if hasattr(self, "activity_list") and self.activity_list.winfo_exists():
                self.activity_list.delete(0, END)
                for log_entry in self.activity_history[-12:]:
                    self.activity_list.insert(END, log_entry)
                self.activity_list.yview_moveto(1.0)

        def _serialize_workspace_state(self):
            geometry = ""
            if self.winfo_exists():
                try:
                    if self.remember_window_geometry_var.get() and self.state() == "normal":
                        geometry = self.geometry()
                except:
                    geometry = ""

            return {
                "profile_data": self._collect_profile_data(),
                "profile_name": self.profile_name_var.get(),
                "profile_choice": self.profile_choice_var.get(),
                "geometry": geometry,
                "recording_data": self.recording_data[-200:],
                "activity_history": self.activity_history[-40:],
                "run_reports": self.run_reports[-20:],
            }

        def _write_workspace_to_disk(self):
            _atomic_write_json(self.workspace_file, self._serialize_workspace_state())

        def _schedule_workspace_save(self, *_args):
            if self._workspace_save_job is not None:
                try:
                    self.after_cancel(self._workspace_save_job)
                except:
                    pass
            self._workspace_save_job = self.after(350, self._persist_workspace_state)

        def _persist_workspace_state(self):
            self._workspace_save_job = None
            try:
                self._write_workspace_to_disk()
            except Exception as exc:
                try:
                    if self.winfo_exists():
                        self.status_var.set(f"Workspace save failed: {exc}")
                        self._append_activity("Workspace save failed.")
                except Exception:
                    pass

        def _load_workspace_from_disk(self):
            if not os.path.exists(self.workspace_file):
                return

            try:
                workspace_state = _load_json_file(self.workspace_file)
            except Exception as exc:
                self.status_var.set(f"Workspace file could not be loaded: {exc}")
                return

            profile_data = workspace_state.get("profile_data")
            if isinstance(profile_data, dict):
                self._apply_profile_data(profile_data)

            self.profile_name_var.set(str(workspace_state.get("profile_name", self.profile_name_var.get())))
            self.profile_choice_var.set(str(workspace_state.get("profile_choice", self.profile_choice_var.get())))

            recording_data = workspace_state.get("recording_data")
            if isinstance(recording_data, list):
                self.recording_data = _normalize_recording_points(recording_data, strict=False)

            activity_history = workspace_state.get("activity_history")
            if isinstance(activity_history, list):
                self.activity_history = [str(entry) for entry in activity_history[-40:]]
                if self.activity_history:
                    self._append_activity("Previous workspace restored.")

            run_reports = workspace_state.get("run_reports")
            if isinstance(run_reports, list):
                self.run_reports = [report for report in run_reports[-20:] if isinstance(report, dict)]

            geometry = workspace_state.get("geometry")
            if geometry and self.remember_window_geometry_var.get():
                try:
                    self.geometry(str(geometry))
                except:
                    pass

        def _handle_state_change(self, *_args):
            self._update_plan_summary()
            self._schedule_workspace_save()

        def _refresh_profile_choices(self):
            profile_names = sorted(self.saved_profiles.keys())
            self.profile_combo.configure(values=profile_names)
            current_choice = self.profile_choice_var.get().strip()
            if current_choice not in profile_names:
                if profile_names:
                    self.profile_choice_var.set(profile_names[0])
                else:
                    self.profile_choice_var.set("")

        def _load_profiles_from_disk(self):
            self.saved_profiles = {}
            if os.path.exists(self.profile_file):
                try:
                    loaded_profiles = _load_json_file(self.profile_file)
                    if isinstance(loaded_profiles, dict):
                        self.saved_profiles = loaded_profiles
                except Exception as exc:
                    self.status_var.set(f"Profile file could not be loaded: {exc}")
            self._refresh_profile_choices()
            self._refresh_profile_state()

        def _save_current_profile(self):
            profile_name = self.profile_name_var.get().strip()
            if not profile_name:
                messagebox.showerror("Profile name required", "Enter a profile name before saving.", parent=self)
                return

            self.saved_profiles[profile_name] = self._collect_profile_data()
            try:
                self._write_profiles_to_disk()
            except Exception as exc:
                messagebox.showerror("Save failed", f"Unable to save profiles.\n{exc}", parent=self)
                return

            self.profile_choice_var.set(profile_name)
            self._refresh_profile_choices()
            self._refresh_profile_state()
            self.status_var.set(f"Saved profile '{profile_name}'.")
            self._append_activity(f"Saved profile '{profile_name}'.")
            self._schedule_workspace_save()

        def _load_selected_profile(self):
            profile_name = self.profile_choice_var.get().strip() or self.profile_name_var.get().strip()
            if not profile_name:
                messagebox.showinfo("Load profile", "Choose a saved profile first.", parent=self)
                return
            if profile_name not in self.saved_profiles:
                messagebox.showerror("Profile missing", f"Profile '{profile_name}' does not exist.", parent=self)
                return

            self._apply_profile_data(self.saved_profiles[profile_name])
            self.profile_name_var.set(profile_name)
            self.profile_choice_var.set(profile_name)
            self.status_var.set(f"Loaded profile '{profile_name}'.")
            self._refresh_profile_state()
            self._append_activity(f"Loaded profile '{profile_name}'.")
            self._schedule_workspace_save()

        def _delete_selected_profile(self):
            profile_name = self.profile_choice_var.get().strip() or self.profile_name_var.get().strip()
            if not profile_name:
                messagebox.showinfo("Delete profile", "Choose a saved profile first.", parent=self)
                return
            if profile_name not in self.saved_profiles:
                messagebox.showerror("Profile missing", f"Profile '{profile_name}' does not exist.", parent=self)
                return
            if not messagebox.askyesno("Delete profile", f"Delete profile '{profile_name}'?", parent=self):
                return

            del self.saved_profiles[profile_name]
            try:
                self._write_profiles_to_disk()
            except Exception as exc:
                messagebox.showerror("Delete failed", f"Unable to update the profile file.\n{exc}", parent=self)
                return

            self._refresh_profile_choices()
            self._refresh_profile_state()
            self.status_var.set(f"Deleted profile '{profile_name}'.")
            self._append_activity(f"Deleted profile '{profile_name}'.")
            self._schedule_workspace_save()

        def _export_profiles(self):
            if not self.saved_profiles:
                messagebox.showinfo("Export profiles", "There are no saved profiles to export.", parent=self)
                return

            export_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile="autoclicker_profiles_export.json",
                parent=self,
            )
            if not export_path:
                return

            try:
                with open(export_path, "w", encoding="utf-8") as export_handle:
                    json.dump(self.saved_profiles, export_handle, indent=2, sort_keys=True)
            except Exception as exc:
                messagebox.showerror("Export failed", f"Unable to export profiles.\n{exc}", parent=self)
                return

            self.status_var.set(f"Exported {len(self.saved_profiles)} profile(s).")
            self._append_activity(f"Exported profiles to {os.path.basename(export_path)}.")

        def _import_profiles(self):
            import_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                parent=self,
            )
            if not import_path:
                return

            try:
                imported_profiles = _load_json_file(import_path)
            except Exception as exc:
                messagebox.showerror("Import failed", f"Unable to read the selected file.\n{exc}", parent=self)
                return

            if not isinstance(imported_profiles, dict):
                messagebox.showerror("Import failed", "The selected file must contain a JSON object of profiles.", parent=self)
                return

            try:
                preview = _preview_profile_import(imported_profiles, self.saved_profiles, self.CLICK_TYPES)
            except Exception as exc:
                messagebox.showerror("Import failed", str(exc), parent=self)
                return

            if preview["valid_count"] == 0:
                messagebox.showinfo("Import profiles", "No valid profiles were found in the selected file.", parent=self)
                return

            warnings_count = sum(len(messages) for messages in preview["warnings_by_profile"].values())
            if preview["invalid_count"] or preview["overwrite_count"] or warnings_count:
                def preview_names(label, names):
                    names = sorted(str(name) for name in names)
                    if not names:
                        return []
                    shown = ", ".join(names[:5])
                    if len(names) > 5:
                        shown = f"{shown}, +{len(names) - 5} more"
                    return [f"{label}: {shown}"]

                invalid_names = [profile["name"] for profile in preview["invalid_profiles"]]
                warning_names = sorted(preview["warnings_by_profile"])
                summary_lines = [
                    f"Valid profiles: {preview['valid_count']}",
                    f"New profiles: {preview['new_count']}",
                    f"Profiles that will overwrite existing profiles: {preview['overwrite_count']}",
                    f"Invalid profiles that will be skipped: {preview['invalid_count']}",
                    f"Warnings: {warnings_count}",
                    "",
                    *preview_names("New", preview["new_profiles"]),
                    *preview_names("Overwrite", preview["overwrites"]),
                    *preview_names("Invalid", invalid_names),
                    *preview_names("Warnings", warning_names),
                    "",
                    "Continue importing the valid profiles?",
                ]
                if not messagebox.askyesno("Import preview", "\n".join(summary_lines), parent=self):
                    self.status_var.set("Profile import cancelled after preview.")
                    return

            self.saved_profiles.update(preview["valid_profiles"])

            try:
                self._write_profiles_to_disk()
            except Exception as exc:
                messagebox.showerror("Import failed", f"Unable to update the local profile file.\n{exc}", parent=self)
                return

            self._refresh_profile_choices()
            self._refresh_profile_state()
            self.status_var.set(f"Imported {preview['valid_count']} profile(s).")
            self._append_activity(
                f"Imported {preview['valid_count']} profile(s) from {os.path.basename(import_path)}."
            )
            self._schedule_workspace_save()

        def _open_path_in_explorer(self, path):
            target_path = path
            if not os.path.exists(target_path):
                target_path = os.path.dirname(target_path) or os.getcwd()

            try:
                os.startfile(target_path)
            except Exception as exc:
                messagebox.showerror("Open failed", f"Unable to open:\n{target_path}\n\n{exc}", parent=self)

        def _open_state_folder(self):
            state_directory = os.path.dirname(self.profile_file)
            try:
                os.makedirs(state_directory, exist_ok=True)
            except Exception as exc:
                messagebox.showerror("Open failed", f"Unable to prepare the state folder.\n{exc}", parent=self)
                return
            self._open_path_in_explorer(state_directory)
            self._append_activity("Opened state folder.")

        def _backup_state_snapshot(self):
            try:
                backup_result = _backup_state_files()
            except Exception as exc:
                messagebox.showerror("Backup failed", f"Unable to back up state files.\n{exc}", parent=self)
                return

            backup_dir = backup_result["backup_dir"]
            copied_count = backup_result["count"]
            manifest_path = backup_result["manifest_path"]
            if copied_count:
                message = f"Backed up {copied_count} state file(s).\n\nFolder:\n{backup_dir}"
            else:
                message = f"No state files were found yet.\n\nCreated manifest:\n{manifest_path}"
            messagebox.showinfo("State backup", message, parent=self)
            self.status_var.set(f"State backup ready: {os.path.basename(backup_dir)}.")
            self._append_activity(f"State backup created with {copied_count} file(s).")

        def _create_support_bundle(self):
            try:
                bundle_result = _build_support_bundle(
                    profile_data=self._collect_profile_data(),
                    activity_history=self.activity_history,
                    run_reports=self.run_reports,
                    state_files={
                        "profiles": self.profile_file,
                        "workspace": self.workspace_file,
                    },
                )
            except Exception as exc:
                messagebox.showerror("Support bundle failed", f"Unable to create the support bundle.\n{exc}", parent=self)
                return

            bundle_dir = bundle_result["bundle_dir"]
            file_count = len(bundle_result["files"]) + bundle_result["backup"]["count"]
            messagebox.showinfo(
                "Support bundle",
                f"Created a support bundle with {file_count} file(s).\n\nFolder:\n{bundle_dir}",
                parent=self,
            )
            self.status_var.set(f"Support bundle ready: {os.path.basename(bundle_dir)}.")
            self._append_activity(f"Support bundle created with {file_count} file(s).")

        def _export_activity_log(self):
            if not self.activity_history:
                messagebox.showinfo("Activity log", "There is no activity history to export yet.", parent=self)
                return

            export_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                initialfile="autoclicker_activity_log.txt",
                parent=self,
            )
            if not export_path:
                return

            try:
                with open(export_path, "w", encoding="utf-8") as export_handle:
                    export_handle.write("\n".join(self.activity_history))
            except Exception as exc:
                messagebox.showerror("Export failed", f"Unable to export the activity log.\n{exc}", parent=self)
                return

            self.status_var.set(f"Exported activity log to {os.path.basename(export_path)}.")
            self._append_activity(f"Exported activity log to {os.path.basename(export_path)}.")

        def _export_session_report(self):
            export_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile="autoclicker_session_report.json",
                parent=self,
            )
            if not export_path:
                return

            payload = _build_session_report_payload(
                self._collect_profile_data(),
                self.activity_history,
                self.run_reports,
                {
                    "profiles": self.profile_file,
                    "workspace": self.workspace_file,
                },
            )

            try:
                _atomic_write_json(export_path, payload, sort_keys=True)
            except Exception as exc:
                messagebox.showerror("Export failed", f"Unable to export the session report.\n{exc}", parent=self)
                return

            self.status_var.set(f"Exported session report to {os.path.basename(export_path)}.")
            self._append_activity(f"Exported session report to {os.path.basename(export_path)}.")

        def _open_health_dashboard(self):
            window = tk.Toplevel(self)
            window.title("Health Check")
            window.geometry("620x520+320+190")
            window.resizable(False, False)
            window.attributes("-topmost", True)
            window.configure(bg="#edf4ff")
            try:
                window.iconbitmap(_resource_path("favicon.ico"))
            except:
                pass

            body = tk.Frame(window, bg="#edf4ff", padx=16, pady=16)
            body.pack(fill="both", expand=True)
            body.columnconfigure(0, weight=1)

            tk.Label(body, text="System Health", bg="#edf4ff", fg="#0f172a", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(body, text="Inspect dependency health, local state files, and current automation context.", bg="#edf4ff", fg="#475569", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=(2, 12))

            report_box = tk.Text(body, height=19, width=72, wrap="word", font=("Consolas", 10), bg="white", fg="#0f172a", relief="flat")
            report_box.grid(row=2, column=0, sticky="nsew")

            button_row = tk.Frame(body, bg="#edf4ff")
            button_row.grid(row=3, column=0, sticky="ew", pady=(12, 0))
            button_row.columnconfigure(0, weight=1)
            button_row.columnconfigure(1, weight=1)
            button_row.columnconfigure(2, weight=1)

            def build_report():
                dependency_names = ("pyautogui", "keyboard", "pystray", "Pillow")
                dependency_lines = []
                for dependency_name in dependency_names:
                    if dependency_name in IMPORT_ERRORS:
                        dependency_lines.append(f"- {dependency_name}: missing ({IMPORT_ERRORS[dependency_name]})")
                    else:
                        dependency_lines.append(f"- {dependency_name}: available")

                workspace_exists = os.path.exists(self.workspace_file)
                profiles_exists = os.path.exists(self.profile_file)
                sequence_running = self.sequence_thread is not None and self.sequence_thread.is_alive()
                click_running = self.worker_thread is not None and self.worker_thread.is_alive()

                sections = [
                    "Platform",
                    f"- App version: {APP_VERSION}",
                    f"- OS: {platform.system()} {platform.release()}",
                    f"- Python: {sys.version.split()[0]}",
                    "",
                    "Dependencies",
                    *dependency_lines,
                    "",
                    "State Files",
                    f"- State directory: {os.path.dirname(self.profile_file)}",
                    f"- Profiles file: {'present' if profiles_exists else 'not created yet'}",
                    f"  {self.profile_file}",
                    f"- Workspace file: {'present' if workspace_exists else 'not created yet'}",
                    f"  {self.workspace_file}",
                    "",
                    "Session",
                    f"- Session clicks: {self.session_clicks}",
                    f"- Recorded points: {len(self.recording_data)}",
                    f"- Saved profiles: {len(self.saved_profiles)}",
                    f"- Click run active: {'yes' if click_running else 'no'}",
                    f"- Sequence active: {'yes' if sequence_running else 'no'}",
                    f"- Playback active: {'yes' if self.is_playing else 'no'}",
                    f"- Recording active: {'yes' if self.is_recording else 'no'}",
                    "",
                    "Window Preferences",
                    f"- Geometry: {self.geometry()}",
                    f"- Theme: {self.theme_var.get()}",
                    f"- Behaviour preset: {self.behaviour_preset_var.get()}",
                    f"- Profile state: {self.profile_state_var.get()}",
                    f"- Run intelligence: {self.run_intelligence_var.get()}",
                    f"- Max action cap: {self.max_actions_var.get()}",
                    f"- PyAutoGUI corner fail-safe: {'enabled' if self.pyautogui_failsafe_var.get() else 'disabled'}",
                    f"- Micro-pause: {self.micro_pause_duration_var.get()}s every {self.micro_pause_every_var.get()} click(s)",
                    f"- Topmost: {'yes' if self.topmost_var.get() else 'no'}",
                    f"- Fullscreen: {'yes' if self.fullscreen_var.get() else 'no'}",
                    f"- Close button action: {'minimize to tray' if self.close_to_tray_var.get() else 'exit app'}",
                    f"- Remember geometry: {'yes' if self.remember_window_geometry_var.get() else 'no'}",
                    f"- Window opacity: {int(self._normalize_window_opacity() * 100)}%",
                    f"- UI scale: {int(self._normalize_ui_scale() * 100)}%",
                ]
                return "\n".join(sections)

            def refresh_report():
                report_box.configure(state="normal")
                report_box.delete("1.0", END)
                report_box.insert("1.0", build_report())
                report_box.configure(state="disabled")

            ttk.Button(button_row, text="Refresh", style="Secondary.TButton", command=refresh_report).grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
            ttk.Button(button_row, text="Open State Folder", style="Secondary.TButton", command=self._open_state_folder).grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(0, 8))
            ttk.Button(button_row, text="Backup State", style="Secondary.TButton", command=self._backup_state_snapshot).grid(row=0, column=2, sticky="ew", pady=(0, 8))
            ttk.Button(button_row, text="Open Profiles File", style="Secondary.TButton", command=lambda: self._open_path_in_explorer(self.profile_file)).grid(row=1, column=0, sticky="ew", padx=(0, 8))
            ttk.Button(button_row, text="Open Workspace File", style="Secondary.TButton", command=lambda: self._open_path_in_explorer(self.workspace_file)).grid(row=1, column=1, sticky="ew", padx=(0, 8))
            ttk.Button(button_row, text="Export Activity", style="Secondary.TButton", command=self._export_activity_log).grid(row=1, column=2, sticky="ew")
            ttk.Button(button_row, text="Create Support Bundle", style="Secondary.TButton", command=self._create_support_bundle).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))

            refresh_report()

        def _open_recording_studio(self):
            window = tk.Toplevel(self)
            window.title("Recording Studio")
            window.geometry("620x520+320+190")
            window.resizable(False, False)
            window.attributes("-topmost", True)
            window.configure(bg="#edf4ff")
            try:
                window.iconbitmap(_resource_path("favicon.ico"))
            except:
                pass

            body = tk.Frame(window, bg="#edf4ff", padx=16, pady=16)
            body.pack(fill="both", expand=True)
            body.columnconfigure(0, weight=1)
            body.columnconfigure(1, weight=1)

            summary_var = tk.StringVar(value="")
            helper_var = tk.StringVar(value="Manage recorded points, then use Playback or import them into a sequence.")
            state = {"snapshot": None, "recording_flag": None}

            tk.Label(body, text="Recording Studio", bg="#edf4ff", fg="#0f172a", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
            tk.Label(body, text="Capture, review, save, load, and trim recorded points without leaving the main app.", bg="#edf4ff", fg="#475569", font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 12))

            list_box = Listbox(body, width=62, height=16, font=("Segoe UI", 10), bg="white", fg="#0f172a", selectbackground="#1d4ed8", activestyle="none", exportselection=False)
            list_box.grid(row=2, column=0, columnspan=2, sticky="ew")

            tk.Label(body, textvariable=summary_var, bg="#edf4ff", fg="#0f766e", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 12))

            def selected_index():
                selection = list_box.curselection()
                return selection[0] if selection else None

            def render_points(preferred_index=None):
                snapshot = tuple(self.recording_data)
                if snapshot == state["snapshot"] and self.is_recording == state["recording_flag"]:
                    return

                current_index = selected_index() if preferred_index is None else preferred_index
                list_box.delete(0, END)
                for index, (x_pos, y_pos) in enumerate(self.recording_data, start=1):
                    list_box.insert(END, f"{index}. ({x_pos}, {y_pos})")

                if current_index is not None and 0 <= current_index < len(self.recording_data):
                    list_box.selection_set(current_index)
                    list_box.activate(current_index)

                summary_var.set(
                    f"{len(self.recording_data)} point(s) captured | recording is {'active' if self.is_recording else 'idle'}"
                )
                state["snapshot"] = snapshot
                state["recording_flag"] = self.is_recording

            def schedule_refresh():
                if not window.winfo_exists():
                    return
                render_points()
                window.after(250, schedule_refresh)

            def capture_cursor_point():
                if not _ensure_dependencies("Recording Studio", ["pyautogui"], parent=window):
                    return

                try:
                    x_pos, y_pos = pyautogui.position()
                except Exception as exc:
                    messagebox.showerror("Capture failed", f"Unable to read the cursor position.\n{exc}", parent=window)
                    return

                self.recording_data.append((int(x_pos), int(y_pos)))
                render_points(len(self.recording_data) - 1)
                helper_var.set(f"Captured point ({x_pos}, {y_pos}).")
                self._append_activity(f"Captured recording point {x_pos}, {y_pos}.")
                self._schedule_workspace_save()

            def use_selected_for_target():
                current_index = selected_index()
                if current_index is None:
                    return
                x_pos, y_pos = self.recording_data[current_index]
                self.target_x_var.set(str(x_pos))
                self.target_y_var.set(str(y_pos))
                helper_var.set(f"Loaded ({x_pos}, {y_pos}) into the main planner.")
                self._append_activity(f"Loaded recording point {x_pos}, {y_pos} into the planner.")

            def undo_last_point():
                if not self.recording_data:
                    return
                removed_point = self.recording_data.pop()
                render_points(len(self.recording_data) - 1 if self.recording_data else None)
                helper_var.set(f"Removed last point {removed_point}.")
                self._append_activity(f"Removed last recording point {removed_point}.")
                self._schedule_workspace_save()

            def delete_selected_point():
                current_index = selected_index()
                if current_index is None:
                    return
                removed_point = self.recording_data.pop(current_index)
                render_points(min(current_index, len(self.recording_data) - 1) if self.recording_data else None)
                helper_var.set(f"Removed point {removed_point}.")
                self._append_activity(f"Removed recording point {removed_point}.")
                self._schedule_workspace_save()

            def clear_points():
                if not self.recording_data:
                    return
                if not messagebox.askyesno("Clear recording", "Remove every recorded point?", parent=window):
                    return
                self.recording_data.clear()
                render_points()
                helper_var.set("Recording cleared.")
                self._append_activity("Cleared all recorded points.")
                self._schedule_workspace_save()

            def save_recording():
                if not self.recording_data:
                    messagebox.showinfo("Recording Studio", "Capture at least one point before saving.", parent=window)
                    return

                file_path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json")],
                    initialfile="autoclicker_recording.json",
                    parent=window,
                )
                if not file_path:
                    return

                try:
                    with open(file_path, "w", encoding="utf-8") as file_handle:
                        json.dump(self.recording_data, file_handle, indent=2)
                except Exception as exc:
                    messagebox.showerror("Save failed", f"Unable to save the recording.\n{exc}", parent=window)
                    return

                helper_var.set(f"Saved {len(self.recording_data)} point(s) to {os.path.basename(file_path)}.")
                self._append_activity(f"Saved recording to {os.path.basename(file_path)}.")

            def load_recording():
                file_path = filedialog.askopenfilename(
                    filetypes=[("JSON files", "*.json")],
                    parent=window,
                )
                if not file_path:
                    return

                try:
                    loaded_points = _normalize_recording_points(_load_json_file(file_path), strict=True)
                except Exception as exc:
                    messagebox.showerror("Load failed", f"Unable to load the recording.\n{exc}", parent=window)
                    return

                self.recording_data = loaded_points
                render_points(0 if self.recording_data else None)
                helper_var.set(f"Loaded {len(self.recording_data)} point(s) from {os.path.basename(file_path)}.")
                self._append_activity(f"Loaded recording from {os.path.basename(file_path)}.")
                self._schedule_workspace_save()

            ttk.Button(body, text="Toggle Record", style="Secondary.TButton", command=self._toggle_recording).grid(row=4, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(body, text="Capture Cursor", style="Secondary.TButton", command=capture_cursor_point).grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(body, text="Use Selected In Planner", style="Secondary.TButton", command=use_selected_for_target).grid(row=5, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(body, text="Playback Recording", style="Secondary.TButton", command=self._play_recording).grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(body, text="Undo Last", style="Secondary.TButton", command=undo_last_point).grid(row=6, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(body, text="Delete Selected", style="Secondary.TButton", command=delete_selected_point).grid(row=6, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(body, text="Save Recording", style="Secondary.TButton", command=save_recording).grid(row=7, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(body, text="Load Recording", style="Secondary.TButton", command=load_recording).grid(row=7, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(body, text="Clear All", style="Secondary.TButton", command=clear_points).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 8))

            tk.Label(body, textvariable=helper_var, bg="#edf4ff", fg="#475569", font=("Segoe UI", 9), wraplength=580, justify=LEFT).grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))

            render_points()
            schedule_refresh()

        def _capture_cursor_position(self):
            try:
                current_x, current_y = pyautogui.position()
                self.target_x_var.set(str(current_x))
                self.target_y_var.set(str(current_y))
                self.status_var.set(f"Captured cursor position at {current_x}, {current_y}.")
                self._append_activity(f"Captured cursor position {current_x}, {current_y}.")
            except Exception as exc:
                messagebox.showerror("Capture failed", f"Unable to read the current cursor position.\n{exc}", parent=self)

        def _swap_coordinates(self):
            current_x = self.target_x_var.get()
            current_y = self.target_y_var.get()
            self.target_x_var.set(current_y)
            self.target_y_var.set(current_x)

        def _update_repeat_state(self):
            if self.repeat_mode_var.get() == "Infinite":
                self.repeat_count_entry.configure(state=DISABLED)
            else:
                self.repeat_count_entry.configure(state=NORMAL)
            self._update_plan_summary()
            self._schedule_workspace_save()

        def _refresh_safety_status(self):
            if not hasattr(self, "safety_status_var"):
                return

            mode = "dry run" if self.dry_run_var.get() else "live clicks"
            fail_safe = "corner fail-safe on" if self.pyautogui_failsafe_var.get() else "corner fail-safe off"
            cap_value = self.max_actions_var.get().strip()
            if cap_value in ("", "0"):
                cap = "no action cap"
            else:
                try:
                    cap_number = int(cap_value)
                    cap = f"{cap_number} action cap" if cap_number > 0 else "action cap needs attention"
                except Exception:
                    cap = "action cap needs attention"
            self.safety_status_var.set(f"Safety: {mode} | {fail_safe} | {cap}")

        def _format_run_intelligence(self, config):
            planned_actions = config["repeat_limit"]
            if config["max_actions"] > 0:
                if planned_actions is None:
                    planned_actions = config["max_actions"]
                else:
                    planned_actions = min(planned_actions, config["max_actions"])

            estimated_duration = config["countdown"]
            if planned_actions is not None:
                estimated_duration += max(0, planned_actions - 1) * config["delay"]
                if config["micro_pause_every"] > 0 and config["micro_pause_duration"] > 0:
                    pause_count = planned_actions // config["micro_pause_every"]
                    if planned_actions > 0 and planned_actions % config["micro_pause_every"] == 0:
                        pause_count = max(0, pause_count - 1)
                    estimated_duration += pause_count * config["micro_pause_duration"]
                run_shape = f"{planned_actions} action(s), about {_format_seconds(estimated_duration)}"
            elif config["runtime_limit"] > 0:
                run_shape = f"runtime capped at {_format_seconds(config['runtime_limit'])}"
            else:
                run_shape = "continuous until stopped"

            if config["delay"] == 0:
                pace = "maximum available pace"
            else:
                pace = f"about {1 / config['delay']:.1f} action(s)/sec"

            warnings = []
            if not (0 <= config["x"] < self.screen_width and 0 <= config["y"] < self.screen_height):
                clamped_x = max(0, min(self.screen_width - 1, config["x"]))
                clamped_y = max(0, min(self.screen_height - 1, config["y"]))
                warnings.append(f"target clamps to {clamped_x}, {clamped_y}")
            if config["delay"] == 0:
                warnings.append("zero delay")
            if config["dry_run"]:
                warnings.append("dry run: no clicks will be sent")
            if config["repeat_limit"] is None and config["runtime_limit"] == 0 and config["max_actions"] == 0:
                warnings.append("no runtime/action cap")
            if not config["pyautogui_failsafe"]:
                warnings.append("corner fail-safe off")

            warning_text = "; ".join(warnings) if warnings else "no immediate warnings"
            return f"{run_shape}; {pace}; {warning_text}."

        def _refresh_run_intelligence(self):
            if not hasattr(self, "run_intelligence_var"):
                return
            try:
                config = self._build_run_config()
            except Exception as exc:
                self.run_intelligence_var.set(f"Needs attention: {exc}")
                return
            self.run_intelligence_var.set(self._format_run_intelligence(config))

        def _refresh_readiness_checklist(self):
            if not hasattr(self, "readiness_var"):
                return
            try:
                config = self._build_run_config()
            except Exception as exc:
                self.readiness_var.set(f"Readiness: fix configuration\n- Review Configuration: {exc}")
                return
            readiness = _build_readiness_checklist(config, (self.screen_width, self.screen_height))
            self.readiness_var.set(_format_readiness_text(readiness))

        def _refresh_profile_state(self):
            if not hasattr(self, "profile_state_var"):
                return
            profile_state = _build_profile_state(
                self.profile_name_var.get(),
                self.profile_choice_var.get(),
                self._collect_profile_data(),
                self.saved_profiles,
            )
            self.profile_state_var.set(_format_profile_state_text(profile_state))

        def _validate_current_plan(self):
            try:
                config = self._build_run_config()
            except ValueError as exc:
                messagebox.showerror("Plan needs attention", str(exc), parent=self)
                return
            summary = self._format_run_intelligence(config)
            readiness = _build_readiness_checklist(config, (self.screen_width, self.screen_height))
            self.run_intelligence_var.set(summary)
            self.readiness_var.set(_format_readiness_text(readiness))
            self.status_var.set(f"Plan validated: {readiness['status']}. {summary}")
            self._append_activity("Run plan validated.")

        def _update_plan_summary(self, *_args):
            click_mode = self.click_mode_var.get()
            delay = self.delay_var.get().strip() or "0.00"
            delay_variance = self.delay_variance_var.get().strip() or "0.00"
            jitter_x = self.jitter_x_var.get().strip() or "0"
            jitter_y = self.jitter_y_var.get().strip() or "0"
            countdown = self.countdown_var.get().strip() or "0"
            runtime_limit = self.runtime_limit_var.get().strip() or "0"
            max_actions = self.max_actions_var.get().strip() or "0"
            stop_hotkey = self.stop_hotkey_var.get().strip() or "manual stop only"
            micro_pause_every = self.micro_pause_every_var.get().strip() or "0"
            micro_pause_duration = self.micro_pause_duration_var.get().strip() or "0.00"
            if self.repeat_mode_var.get() == "Burst Count":
                run_shape = f"{self.repeat_count_var.get().strip() or '?'} action(s)"
            else:
                run_shape = "continuous"
            style_flags = []
            if self.human_like_var.get():
                style_flags.append("human-like motion")
            if self.play_sound_var.get():
                style_flags.append("finish sound")
            if self.dry_run_var.get():
                style_flags.append("dry run")
            if max_actions not in ("0", ""):
                style_flags.append(f"action cap {max_actions}")
            if self.pyautogui_failsafe_var.get():
                style_flags.append("corner fail-safe")
            if micro_pause_every not in ("0", "") and micro_pause_duration not in ("0", "0.00", ""):
                style_flags.append(f"micro-pause every {micro_pause_every}")
            style_summary = ", ".join(style_flags) if style_flags else "standard run"
            self._refresh_preset_summary()
            self.plan_var.set(
                f"{click_mode} at ({self.target_x_var.get().strip() or '?'}, {self.target_y_var.get().strip() or '?'}) "
                f"with a {delay}s gap +/- {delay_variance}s, jitter +/-({jitter_x}, {jitter_y}), {countdown}s countdown, "
                f"running as {run_shape}, capped at {runtime_limit}s, stopped by {stop_hotkey}, using {style_summary}, "
                f"preset '{self.behaviour_preset_var.get()}', micro-pause {micro_pause_duration}s every {micro_pause_every} click(s)."
            )
            self._refresh_safety_status()
            self._refresh_readiness_checklist()
            self._refresh_profile_state()
            self._refresh_run_intelligence()

        def _refresh_live_cursor(self):
            try:
                current_x, current_y = pyautogui.position()
                self.cursor_var.set(f"Cursor: {current_x}, {current_y}")
            except:
                self.cursor_var.set("Cursor: unavailable")

            if self.winfo_exists():
                self.after(200, self._refresh_live_cursor)

        def _pump_ui_queue(self):
            try:
                while True:
                    action, payload = self.ui_queue.get_nowait()
                    if action == "status":
                        self.status_var.set(payload)
                    elif action == "progress":
                        count, elapsed, last_point = payload
                        action_label = "simulated action(s)" if self.active_run_was_dry_run else "click action(s)"
                        self.session_var.set(
                            f"Active run: {count} {action_label} processed over {elapsed:.2f} second(s). "
                            f"Last point: {last_point[0]}, {last_point[1]}."
                        )
                    elif action == "finished":
                        total_actions, elapsed, last_click_point = payload
                        self._finish_run(total_actions, elapsed, last_click_point)
            except queue.Empty:
                pass

            if self.winfo_exists():
                self.after(100, self._pump_ui_queue)

        def _build_run_config(self):
            click_mode = self.click_mode_var.get()
            if click_mode not in self.CLICK_TYPES:
                raise ValueError("Choose a valid click type.")

            x_pos = int(self.target_x_var.get())
            y_pos = int(self.target_y_var.get())
            delay_seconds = float(self.delay_var.get())
            delay_variance_seconds = float(self.delay_variance_var.get())
            jitter_x = int(self.jitter_x_var.get())
            jitter_y = int(self.jitter_y_var.get())
            countdown_seconds = float(self.countdown_var.get())
            runtime_limit_seconds = float(self.runtime_limit_var.get())
            max_actions = int(self.max_actions_var.get())
            micro_pause_every = int(self.micro_pause_every_var.get())
            micro_pause_duration = float(self.micro_pause_duration_var.get())
            if delay_seconds < 0:
                raise ValueError("Delay must be zero or greater.")
            if delay_variance_seconds < 0:
                raise ValueError("Delay variance must be zero or greater.")
            if jitter_x < 0 or jitter_y < 0:
                raise ValueError("Jitter values must be zero or greater.")
            if countdown_seconds < 0:
                raise ValueError("Countdown must be zero or greater.")
            if runtime_limit_seconds < 0:
                raise ValueError("Runtime cap must be zero or greater.")
            if max_actions < 0:
                raise ValueError("Max actions cap must be zero or greater.")
            if micro_pause_every < 0:
                raise ValueError("Micro-pause frequency must be zero or greater.")
            if micro_pause_duration < 0:
                raise ValueError("Micro-pause duration must be zero or greater.")

            stop_hotkey = self.stop_hotkey_var.get().strip()
            if self.repeat_mode_var.get() == "Infinite":
                repeat_limit = None
                if not stop_hotkey:
                    raise ValueError("Set a stop hotkey before starting an infinite run.")
            else:
                repeat_limit = int(self.repeat_count_var.get())
                if repeat_limit < 1:
                    raise ValueError("Burst count must be at least 1.")

            return {
                "x": x_pos,
                "y": y_pos,
                "delay": delay_seconds,
                "delay_variance": delay_variance_seconds,
                "jitter_x": jitter_x,
                "jitter_y": jitter_y,
                "countdown": countdown_seconds,
                "runtime_limit": runtime_limit_seconds,
                "max_actions": max_actions,
                "stop_hotkey": stop_hotkey,
                "repeat_limit": repeat_limit,
                "button": self.CLICK_TYPES[click_mode][0],
                "clicks": self.CLICK_TYPES[click_mode][1],
                "click_mode": click_mode,
                "behaviour_preset": self.behaviour_preset_var.get(),
                "micro_pause_every": micro_pause_every,
                "micro_pause_duration": micro_pause_duration,
                "human_like": self.human_like_var.get(),
                "dry_run": self.dry_run_var.get(),
                "pyautogui_failsafe": self.pyautogui_failsafe_var.get(),
            }

        def _stop_requested(self, stop_hotkey):
            if self.stop_event.is_set():
                return True
            if not stop_hotkey:
                return False

            try:
                if keyboard.is_pressed(stop_hotkey):
                    self.stop_reason = "hotkey"
                    self.stop_event.set()
                    if not self.hotkey_notified:
                        self.hotkey_notified = True
                        self.ui_queue.put(("status", f"Stop hotkey '{stop_hotkey}' pressed. Finishing the current loop."))
                    return True
            except:
                pass

            return False

        def _click_worker(self, config):
            previous_failsafe = getattr(pyautogui, "FAILSAFE", True)
            total_actions = 0
            started_at = time.perf_counter()
            last_progress_update = started_at
            last_click_point = (config["x"], config["y"])

            if config["countdown"] > 0:
                remaining = config["countdown"]
                last_announced = None
                while remaining > 0:
                    if self._stop_requested(config["stop_hotkey"]):
                        elapsed = time.perf_counter() - started_at
                        self.ui_queue.put(("finished", (total_actions, elapsed, last_click_point)))
                        return
                    announce_value = int(remaining)
                    if remaining > announce_value:
                        announce_value += 1
                    if announce_value != last_announced:
                        self.ui_queue.put(("status", f"Starting in {announce_value}s. Use Stop or {config['stop_hotkey'] or 'manual stop'} to cancel."))
                        last_announced = announce_value
                    sleep_slice = min(0.1, remaining)
                    time.sleep(sleep_slice)
                    remaining -= sleep_slice

            try:
                pyautogui.FAILSAFE = bool(config["pyautogui_failsafe"])
            except Exception:
                pass

            while not self._stop_requested(config["stop_hotkey"]):
                elapsed_before_click = time.perf_counter() - started_at
                if config["runtime_limit"] > 0 and elapsed_before_click >= config["runtime_limit"]:
                    self.stop_reason = "runtime_limit"
                    break

                click_x = config["x"]
                click_y = config["y"]

                try:
                    if config["human_like"]:
                        if config["jitter_x"] > 0:
                            click_x += int(random.gauss(0, config["jitter_x"] / 2))
                        if config["jitter_y"] > 0:
                            click_y += int(random.gauss(0, config["jitter_y"] / 2))
                        if not config["dry_run"]:
                            pyautogui.moveTo(
                                click_x + random.randint(-2, 2),
                                click_y + random.randint(-2, 2),
                                duration=random.uniform(0.01, 0.05),
                            )
                    else:
                        if config["jitter_x"] > 0:
                            click_x += random.randint(-config["jitter_x"], config["jitter_x"])
                        if config["jitter_y"] > 0:
                            click_y += random.randint(-config["jitter_y"], config["jitter_y"])

                    click_x = max(0, min(self.screen_width - 1, click_x))
                    click_y = max(0, min(self.screen_height - 1, click_y))
                    last_click_point = (click_x, click_y)

                    if not config["dry_run"]:
                        pyautogui.click(
                            x=click_x,
                            y=click_y,
                            button=config["button"],
                            clicks=config["clicks"],
                            interval=random.uniform(0.01, 0.03) if config["clicks"] > 1 else 0.0,
                        )
                except Exception as exc:
                    if exc.__class__.__name__ == "FailSafeException":
                        self.stop_reason = "failsafe"
                        self.ui_queue.put(("status", "PyAutoGUI corner fail-safe triggered. Run stopped."))
                    else:
                        self.stop_reason = "error"
                        self.ui_queue.put(("status", f"Click error: {exc}"))
                    break
                total_actions += 1
                if not config["dry_run"]:
                    self.session_clicks += 1

                now = time.perf_counter()
                if total_actions == 1 or now - last_progress_update >= 0.25:
                    self.ui_queue.put(("progress", (total_actions, now - started_at, last_click_point)))
                    last_progress_update = now

                if (
                    config["max_actions"] > 0
                    and total_actions >= config["max_actions"]
                    and (config["repeat_limit"] is None or config["max_actions"] < config["repeat_limit"])
                ):
                    self.stop_reason = "max_actions"
                    break

                if config["repeat_limit"] is not None and total_actions >= config["repeat_limit"]:
                    self.stop_reason = "completed"
                    break

                if (
                    config["micro_pause_every"] > 0
                    and config["micro_pause_duration"] > 0
                    and total_actions % config["micro_pause_every"] == 0
                ):
                    self.ui_queue.put(
                        ("status", f"Micro-pause: resting for {config['micro_pause_duration']:.2f}s after {total_actions} action(s).")
                    )
                    wake_at = time.perf_counter() + config["micro_pause_duration"]
                    while time.perf_counter() < wake_at:
                        if config["runtime_limit"] > 0 and time.perf_counter() - started_at >= config["runtime_limit"]:
                            self.stop_reason = "runtime_limit"
                            break
                        if self._stop_requested(config["stop_hotkey"]):
                            break
                        time.sleep(min(0.02, wake_at - time.perf_counter()))
                    if self.stop_reason == "runtime_limit":
                        break

                actual_delay = config["delay"]
                if config["delay_variance"] > 0:
                    actual_delay = max(0.0, config["delay"] + random.uniform(-config["delay_variance"], config["delay_variance"]))

                if actual_delay > 0:
                    wake_at = time.perf_counter() + actual_delay
                    while time.perf_counter() < wake_at:
                        if config["runtime_limit"] > 0 and time.perf_counter() - started_at >= config["runtime_limit"]:
                            self.stop_reason = "runtime_limit"
                            break
                        if self._stop_requested(config["stop_hotkey"]):
                            break
                        time.sleep(min(0.02, wake_at - time.perf_counter()))
                    if self.stop_reason == "runtime_limit":
                        break

            try:
                pyautogui.FAILSAFE = previous_failsafe
            except Exception:
                pass
            elapsed = time.perf_counter() - started_at
            self.ui_queue.put(("finished", (total_actions, elapsed, last_click_point)))

        def _finish_run(self, total_actions, elapsed, last_click_point):
            self.worker_thread = None
            if hasattr(self, "start_button"):
                self.start_button.configure(state=NORMAL)
            self.stop_button.configure(state=DISABLED)
            final_stop_reason = self.stop_reason
            action_label = "simulated action(s)" if self.active_run_was_dry_run else "click action(s)"
            run_prefix = "Dry run" if self.active_run_was_dry_run else "Run"

            if self.was_minimized_for_run and self.restore_after_run_var.get():
                try:
                    self.deiconify()
                    self.lift()
                except:
                    pass
            self.was_minimized_for_run = False

            if self.play_sound_var.get() and winsound:
                try:
                    winsound.Beep(1000, 200)
                    winsound.Beep(1200, 250)
                except:
                    pass

            if final_stop_reason == "completed":
                self.status_var.set(f"{run_prefix} complete. Processed {total_actions} {action_label}.")
                self._append_activity(f"{run_prefix} finished after {total_actions} {action_label}.")
            elif final_stop_reason == "hotkey":
                self.status_var.set(f"{run_prefix} stopped by hotkey after {total_actions} {action_label}.")
                self._append_activity(f"{run_prefix} stopped by hotkey after {total_actions} {action_label}.")
            elif final_stop_reason == "manual":
                self.status_var.set(f"{run_prefix} stopped manually after {total_actions} {action_label}.")
                self._append_activity(f"{run_prefix} stopped manually after {total_actions} {action_label}.")
            elif final_stop_reason == "runtime_limit":
                self.status_var.set(f"Runtime cap reached after {total_actions} {action_label}.")
                self._append_activity(f"Runtime cap reached after {total_actions} {action_label}.")
            elif final_stop_reason == "max_actions":
                self.status_var.set(f"Max action cap reached after {total_actions} {action_label}.")
                self._append_activity(f"Max action cap reached after {total_actions} {action_label}.")
            elif final_stop_reason == "failsafe":
                self.status_var.set(f"Corner fail-safe stopped the run after {total_actions} {action_label}.")
                self._append_activity(f"Corner fail-safe stopped the run after {total_actions} {action_label}.")
            elif final_stop_reason == "error":
                self.status_var.set(f"{run_prefix} stopped after an automation error at {total_actions} {action_label}.")
                self._append_activity(f"{run_prefix} stopped after an automation error at {total_actions} {action_label}.")
            else:
                self.status_var.set(f"{run_prefix} finished after {total_actions} {action_label}.")
                self._append_activity(f"{run_prefix} finished after {total_actions} {action_label}.")

            self.session_var.set(f"Last session: {total_actions} {action_label} across {elapsed:.2f} second(s).")
            self.last_run_var.set(
                f"{run_prefix}: {self.click_mode_var.get()} at ({self.target_x_var.get()}, {self.target_y_var.get()}) "
                f"for {elapsed:.2f}s, resulting in {total_actions} action(s). Last point: {last_click_point[0]}, {last_click_point[1]}."
            )
            self.run_reports.append(
                {
                    "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
                    "dry_run": self.active_run_was_dry_run,
                    "stop_reason": final_stop_reason,
                    "actions": total_actions,
                    "elapsed_seconds": round(elapsed, 3),
                    "last_point": [int(last_click_point[0]), int(last_click_point[1])],
                    "click_mode": self.click_mode_var.get(),
                    "target": [self.target_x_var.get(), self.target_y_var.get()],
                    "run_intelligence": self.run_intelligence_var.get(),
                }
            )
            self.run_reports = self.run_reports[-40:]
            self.stop_reason = "idle"
            self.active_run_was_dry_run = False
            self._schedule_workspace_save()

        def startclick(self):
            if self.worker_thread and self.worker_thread.is_alive():
                self.status_var.set("A click run is already active.")
                return
            if self.is_playing:
                self.status_var.set("Playback is active. Stop playback before starting a click run.")
                return

            try:
                config = self._build_run_config()
            except ValueError as exc:
                messagebox.showerror("Invalid configuration", str(exc), parent=self)
                return

            self.stop_event.clear()
            self.stop_reason = "running"
            self.hotkey_notified = False
            self.active_run_was_dry_run = bool(config["dry_run"])
            if hasattr(self, "start_button"):
                self.start_button.configure(state=DISABLED)
            self.stop_button.configure(state=NORMAL)
            self.session_var.set("Starting dry run..." if config["dry_run"] else "Starting click run...")
            if config["countdown"] > 0:
                self.status_var.set(f"Countdown armed for {config['countdown']:.2f}s. Use Stop or the configured hotkey to cancel.")
            else:
                self.status_var.set("Dry run started. No clicks will be sent." if config["dry_run"] else "Run started. Use Stop or the configured hotkey to end it.")
            self._append_activity(
                f"{'Dry run' if config['dry_run'] else 'Run'} started at {config['x']}, {config['y']} using {config['click_mode']}."
            )

            self.worker_thread = threading.Thread(target=self._click_worker, args=(config,), daemon=True)
            self.worker_thread.start()

            if self.minimize_on_start_var.get():
                self.was_minimized_for_run = True
                self.iconify()

            self._schedule_workspace_save()

        def stopclick(self):
            if self.worker_thread and self.worker_thread.is_alive():
                self.stop_reason = "manual"
                self.stop_event.set()
                self.status_var.set("Stop requested. Waiting for the current loop to finish.")
                self._append_activity("Stop requested for the active run.")
            elif self.sequence_thread and self.sequence_thread.is_alive():
                self.stop_event.set()
                self.status_var.set("Stopping coordinate sequence after the current step.")
                self._append_activity("Stop requested for coordinate sequence.")
            elif self.is_playing:
                self.stop_event.set()
                self.status_var.set("Stopping playback after the current point.")
                self._append_activity("Stop requested for playback.")


        def _apply_theme(self):
            palette = self._theme_palette()
            self._refresh_ttk_styles(palette)
            self.configure(bg=palette["main_bg"])

            def walk(widget):
                try:
                    current_bg = widget.cget("bg")
                    if current_bg == "#dbe7f2":
                        widget.configure(bg=palette["main_bg"])
                    elif current_bg == "#f8fafc":
                        widget.configure(bg=palette["card_bg"])
                    elif current_bg == "#edf4ff":
                        widget.configure(bg=palette["alt_bg"])
                    elif current_bg == "#0f172a":
                        widget.configure(bg=palette["hero_bg"])
                    elif current_bg == "#1e293b":
                        widget.configure(bg=palette["hero_chip_bg"])
                    elif current_bg == "white":
                        widget.configure(bg=palette["list_bg"])

                    current_fg = widget.cget("fg")
                    if current_fg == "#0f172a":
                        widget.configure(fg=palette["text"])
                    elif current_fg == "#475569":
                        widget.configure(fg=palette["sub"])
                    elif current_fg in ("white", "#f8fafc"):
                        widget.configure(fg=palette["hero_fg"])
                    elif current_fg == "#cbd5e1":
                        widget.configure(fg=palette["hero_sub"])
                    elif current_fg == "#334155":
                        widget.configure(fg=palette["sub"])
                    elif current_fg == "#0f766e":
                        widget.configure(fg=palette["accent"])

                    if isinstance(widget, (tk.Frame, tk.Label, tk.Canvas, tk.Text, tk.Listbox)):
                        try:
                            widget.configure(highlightbackground=palette["border"])
                        except Exception:
                            pass

                    if isinstance(widget, tk.Text):
                        widget.configure(insertbackground=palette["text"])
                    if isinstance(widget, tk.Listbox):
                        widget.configure(selectbackground=palette["select_bg"], selectforeground=palette["hero_fg"])
                except Exception:
                    pass

                for child in widget.winfo_children():
                    walk(child)

            walk(self)
            self._refresh_window_summary()
            self.after_idle(self._update_main_scroll_region)

        def _open_settings_window(self):
            palette = self._theme_palette()
            window = tk.Toplevel(self)
            window.title("Window Settings")
            window.geometry("620x560+280+160")
            window.minsize(500, 420)
            window.resizable(True, True)
            window.attributes("-topmost", True)
            window.configure(bg=palette["card_bg"])
            try:
                window.iconbitmap(_resource_path("favicon.ico"))
            except:
                pass

            body, settings_canvas = _create_scrollable_shell(window, palette["card_bg"], min_width=560, padx=16, pady=16)
            body.columnconfigure(0, weight=1)

            def on_settings_mousewheel(event):
                if event.delta == 0:
                    return
                step = -1 if event.delta > 0 else 1
                if event.state & 0x1:
                    settings_canvas.xview_scroll(step, "units")
                else:
                    settings_canvas.yview_scroll(step, "units")

            window.bind("<MouseWheel>", on_settings_mousewheel)

            def make_section(row, title):
                frame = tk.Frame(
                    body,
                    bg=palette["card_bg"],
                    highlightbackground=palette["border"],
                    highlightthickness=1,
                    padx=14,
                    pady=12,
                )
                frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
                frame.columnconfigure(0, weight=1)
                tk.Label(frame, text=title, bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
                return frame

            tk.Label(body, text="Window Settings", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(body, textvariable=self.window_summary_var, bg=palette["card_bg"], fg=palette["accent"], font=("Segoe UI", 9, "bold"), wraplength=520, justify=LEFT).grid(row=1, column=0, sticky="w", pady=(4, 14))

            appearance = make_section(2, "Appearance")
            appearance.columnconfigure(1, weight=1)
            tk.Label(appearance, text="Theme", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 8))
            theme_combo = ttk.Combobox(appearance, textvariable=self.theme_var, values=("Light", "Dark", "Ocean"), state="readonly")
            theme_combo.grid(row=1, column=1, sticky="ew", pady=(0, 8))
            theme_combo.bind("<<ComboboxSelected>>", lambda _event: self._apply_theme())

            tk.Label(appearance, text="Window opacity", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 8))
            ttk.Scale(appearance, variable=self.window_opacity_var, from_=0.70, to=1.00, style="App.Horizontal.TScale", command=lambda _value: self._apply_window_preferences()).grid(row=2, column=1, sticky="ew", pady=(0, 8))
            opacity_row = tk.Frame(appearance, bg=palette["card_bg"])
            opacity_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            for index, (label, value) in enumerate((("70%", 0.70), ("85%", 0.85), ("100%", 1.0))):
                opacity_row.columnconfigure(index, weight=1)
                ttk.Button(opacity_row, text=label, style="Chip.TButton", command=lambda preset=value: self._set_window_opacity_preset(preset)).grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0))

            tk.Label(appearance, text="UI scale", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 8))
            ttk.Scale(appearance, variable=self.ui_scale_var, from_=0.90, to=1.35, style="App.Horizontal.TScale", command=lambda _value: self._apply_window_preferences()).grid(row=4, column=1, sticky="ew", pady=(0, 8))
            scale_row = tk.Frame(appearance, bg=palette["card_bg"])
            scale_row.grid(row=5, column=0, columnspan=2, sticky="ew")
            for index, (label, value) in enumerate((("90%", 0.90), ("100%", 1.0), ("115%", 1.15), ("130%", 1.30))):
                scale_row.columnconfigure(index, weight=1)
                ttk.Button(scale_row, text=label, style="Chip.TButton", command=lambda preset=value: self._set_ui_scale_preset(preset)).grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0))

            behavior = make_section(3, "Desktop Behavior")
            ttk.Checkbutton(behavior, text="Keep window on top", variable=self.topmost_var, style="App.TCheckbutton").grid(row=1, column=0, sticky="w", pady=(0, 6))
            ttk.Checkbutton(behavior, text="Minimize while clicking", variable=self.minimize_on_start_var, style="App.TCheckbutton").grid(row=2, column=0, sticky="w", pady=(0, 6))
            ttk.Checkbutton(behavior, text="Restore after run", variable=self.restore_after_run_var, style="App.TCheckbutton").grid(row=3, column=0, sticky="w", pady=(0, 6))
            ttk.Checkbutton(behavior, text="Close button sends app to tray", variable=self.close_to_tray_var, style="App.TCheckbutton").grid(row=4, column=0, sticky="w", pady=(0, 6))
            ttk.Checkbutton(behavior, text="Remember size and position", variable=self.remember_window_geometry_var, style="App.TCheckbutton").grid(row=5, column=0, sticky="w", pady=(0, 6))
            ttk.Checkbutton(behavior, text="Fullscreen mode", variable=self.fullscreen_var, style="App.TCheckbutton").grid(row=6, column=0, sticky="w")

            layout = make_section(4, "Layout Presets")
            for index in range(3):
                layout.columnconfigure(index, weight=1)
            ttk.Button(layout, text="Compact", style="Secondary.TButton", command=lambda: self._set_window_size_preset(920, 640)).grid(row=1, column=0, sticky="ew")
            ttk.Button(layout, text="Wide", style="Secondary.TButton", command=lambda: self._set_window_size_preset(1180, 760)).grid(row=1, column=1, sticky="ew", padx=8)
            ttk.Button(layout, text="Studio", style="Secondary.TButton", command=lambda: self._set_window_size_preset(1360, 860)).grid(row=1, column=2, sticky="ew")
            ttk.Button(layout, text="Fit to Screen", style="Secondary.TButton", command=self._fit_window_to_screen).grid(row=2, column=0, sticky="ew", pady=(8, 0))
            ttk.Button(layout, text="Center", style="Secondary.TButton", command=self._center_window).grid(row=2, column=1, sticky="ew", padx=8, pady=(8, 0))
            ttk.Button(layout, text="Save Current", style="Secondary.TButton", command=self._remember_current_window_layout).grid(row=2, column=2, sticky="ew", pady=(8, 0))

            support = make_section(5, "Maintenance")
            support.columnconfigure(0, weight=1)
            support.columnconfigure(1, weight=1)
            ttk.Button(support, text="Reset Visuals", style="Secondary.TButton", command=self._reset_visual_preferences).grid(row=1, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(support, text="Reset Layout", style="Secondary.TButton", command=self._reset_window_layout).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(support, text="Health Check", style="Secondary.TButton", command=self._open_health_dashboard).grid(row=2, column=0, sticky="ew")
            ttk.Button(support, text="Open State Folder", style="Secondary.TButton", command=self._open_state_folder).grid(row=2, column=1, sticky="ew", padx=(8, 0))

            footer_row = tk.Frame(body, bg=palette["card_bg"])
            footer_row.grid(row=6, column=0, sticky="ew")
            footer_row.columnconfigure(0, weight=1)
            footer_row.columnconfigure(1, weight=1)
            ttk.Button(footer_row, text="Restart Program", style="Secondary.TButton", command=self._restart_program).grid(row=0, column=0, sticky="ew", padx=(0, 8))
            ttk.Button(footer_row, text="Close", style="Secondary.TButton", command=window.destroy).grid(row=0, column=1, sticky="ew")

        def _open_sequence_builder(self):
            if not _ensure_dependencies("Coordinate Sequence", ["pyautogui"], parent=self):
                return

            window = tk.Toplevel(self)
            window.title("Coordinate Sequence")
            window.geometry("660x540+300+180")
            window.resizable(False, False)
            window.attributes("-topmost", True)
            window.configure(bg="#edf4ff")
            try:
                window.iconbitmap(_resource_path("favicon.ico"))
            except:
                pass

            steps = []
            x_var = tk.StringVar(value=self.target_x_var.get())
            y_var = tk.StringVar(value=self.target_y_var.get())
            action_var = tk.StringVar(value=self.click_mode_var.get())
            delay_var = tk.StringVar(value=self.delay_var.get())
            summary_var = tk.StringVar(value="0 step(s) | 0.00s total wait")
            helper_var = tk.StringVar(value="Build, reorder, or import a click path before running it.")

            body = tk.Frame(window, bg="#edf4ff", padx=16, pady=16)
            body.pack(fill="both", expand=True)
            body.columnconfigure(0, weight=1)
            body.columnconfigure(1, weight=1)

            tk.Label(body, text="Coordinate Sequence Builder", bg="#edf4ff", fg="#0f172a", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
            tk.Label(body, text="Build a short step-by-step click path, validate it, and run it once.", bg="#edf4ff", fg="#475569", font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 12))

            list_box = Listbox(body, width=64, height=14, font=("Segoe UI", 10), bg="white", fg="#0f172a", selectbackground="#1d4ed8", activestyle="none")
            list_box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

            tk.Label(body, textvariable=summary_var, bg="#edf4ff", fg="#0f766e", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))

            def normalize_steps(raw_steps):
                return _normalize_sequence_steps(raw_steps, self.CLICK_TYPES)

            def selected_index():
                selection = list_box.curselection()
                return selection[0] if selection else None

            def update_summary():
                total_wait = sum(step[3] for step in steps)
                summary_var.set(f"{len(steps)} step(s) | {total_wait:.2f}s total wait")

            def render_steps(selected_step=None):
                list_box.delete(0, END)
                for index, (x_pos, y_pos, action_name, delay_seconds) in enumerate(steps, start=1):
                    list_box.insert(END, f"{index}. {action_name} at ({x_pos}, {y_pos}) then wait {delay_seconds:.2f}s")
                update_summary()
                if selected_step is not None and 0 <= selected_step < len(steps):
                    list_box.selection_clear(0, END)
                    list_box.selection_set(selected_step)
                    list_box.activate(selected_step)

            def add_step():
                try:
                    x_pos = int(x_var.get())
                    y_pos = int(y_var.get())
                    delay_seconds = float(delay_var.get())
                    if delay_seconds < 0:
                        raise ValueError
                except:
                    messagebox.showerror("Invalid step", "Enter valid X, Y, and delay values.", parent=window)
                    return

                steps.append((x_pos, y_pos, action_var.get(), delay_seconds))
                render_steps(len(steps) - 1)
                helper_var.set("Step added to the sequence.")

            def add_cursor_step():
                try:
                    current_x, current_y = pyautogui.position()
                    x_var.set(str(current_x))
                    y_var.set(str(current_y))
                    add_step()
                except Exception as exc:
                    messagebox.showerror("Capture failed", f"Unable to read the cursor position.\n{exc}", parent=window)

            def import_recording():
                if not self.recording_data:
                    messagebox.showinfo("Sequence builder", "There is no active recording to import.", parent=window)
                    return

                try:
                    delay_seconds = float(delay_var.get())
                    if delay_seconds < 0:
                        raise ValueError
                except:
                    messagebox.showerror("Invalid delay", "Enter a valid delay before importing recorded points.", parent=window)
                    return

                for x_pos, y_pos in self.recording_data:
                    steps.append((int(x_pos), int(y_pos), action_var.get(), delay_seconds))
                render_steps(len(steps) - 1)
                helper_var.set(f"Imported {len(self.recording_data)} recorded point(s).")

            def duplicate_step():
                current_step = selected_index()
                if current_step is None:
                    return
                steps.insert(current_step + 1, steps[current_step])
                render_steps(current_step + 1)
                helper_var.set("Selected step duplicated.")

            def move_step(offset):
                current_step = selected_index()
                if current_step is None:
                    return

                new_index = current_step + offset
                if new_index < 0 or new_index >= len(steps):
                    return

                steps[current_step], steps[new_index] = steps[new_index], steps[current_step]
                render_steps(new_index)
                helper_var.set("Selected step moved.")

            def delete_step():
                current_step = selected_index()
                if current_step is None:
                    return
                del steps[current_step]
                render_steps(min(current_step, len(steps) - 1) if steps else None)
                helper_var.set("Selected step removed.")

            def clear_steps():
                if not steps:
                    return
                if not messagebox.askyesno("Clear sequence", "Remove every step from the current sequence?", parent=window):
                    return
                steps.clear()
                render_steps()
                helper_var.set("Sequence cleared.")

            def run_sequence_worker(sequence_copy):
                completed_steps = 0
                try:
                    pyautogui.FAILSAFE = False
                    for x_pos, y_pos, action_name, delay_seconds in sequence_copy:
                        if self.stop_event.is_set():
                            self.ui_queue.put(("status", f"Coordinate sequence stopped after {completed_steps} step(s)."))
                            self._append_activity(f"Sequence stopped after {completed_steps} step(s).")
                            return

                        button_name, click_count = self.CLICK_TYPES[action_name]
                        pyautogui.click(x=x_pos, y=y_pos, button=button_name, clicks=click_count, interval=0.02 if click_count > 1 else 0.0)
                        completed_steps += 1

                        if delay_seconds > 0:
                            wake_at = time.perf_counter() + delay_seconds
                            while time.perf_counter() < wake_at:
                                if self.stop_event.is_set():
                                    self.ui_queue.put(("status", f"Coordinate sequence stopped after {completed_steps} step(s)."))
                                    self._append_activity(f"Sequence stopped after {completed_steps} step(s).")
                                    return
                                time.sleep(min(0.02, wake_at - time.perf_counter()))

                    self.ui_queue.put(("status", f"Coordinate sequence complete. Ran {completed_steps} step(s)."))
                    self._append_activity(f"Sequence complete. Ran {completed_steps} step(s).")
                except Exception as exc:
                    self.ui_queue.put(("status", f"Sequence error: {exc}"))
                    self._append_activity(f"Sequence error: {exc}")
                finally:
                    self.sequence_thread = None
                    self.stop_event.clear()

            def run_sequence():
                if not steps:
                    messagebox.showinfo("Sequence builder", "Add at least one step before running the sequence.", parent=window)
                    return
                if self.worker_thread and self.worker_thread.is_alive():
                    messagebox.showinfo("Sequence builder", "Stop the active click run before starting a sequence.", parent=window)
                    return
                if self.sequence_thread and self.sequence_thread.is_alive():
                    messagebox.showinfo("Sequence builder", "A sequence is already running.", parent=window)
                    return
                if self.is_playing:
                    messagebox.showinfo("Sequence builder", "Stop playback before starting a sequence.", parent=window)
                    return

                sequence_copy = list(steps)
                self.stop_event.clear()
                self.status_var.set(f"Running coordinate sequence with {len(sequence_copy)} step(s).")
                self._append_activity(f"Sequence started with {len(sequence_copy)} step(s).")
                self.sequence_thread = threading.Thread(target=run_sequence_worker, args=(sequence_copy,), daemon=True)
                self.sequence_thread.start()

            def save_sequence():
                if not steps:
                    messagebox.showinfo("Sequence builder", "Add at least one step before saving.", parent=window)
                    return

                file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], parent=window)
                if not file_path:
                    return

                try:
                    with open(file_path, "w", encoding="utf-8") as file_handle:
                        json.dump(steps, file_handle, indent=2)
                except Exception as exc:
                    messagebox.showerror("Save failed", f"Unable to save the sequence.\n{exc}", parent=window)
                    return

                helper_var.set(f"Sequence saved to {os.path.basename(file_path)}.")

            def load_sequence():
                file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], parent=window)
                if not file_path:
                    return

                try:
                    normalized_steps = normalize_steps(_load_json_file(file_path))
                except Exception as exc:
                    messagebox.showerror("Load failed", f"Unable to load the sequence.\n{exc}", parent=window)
                    return

                steps.clear()
                steps.extend(normalized_steps)
                render_steps(0 if steps else None)
                helper_var.set(f"Loaded {len(steps)} validated step(s).")

            tk.Label(body, text="X", bg="#edf4ff", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w")
            ttk.Entry(body, textvariable=x_var, width=12).grid(row=5, column=0, sticky="w", pady=(4, 8))
            tk.Label(body, text="Y", bg="#edf4ff", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=4, column=1, sticky="w")
            ttk.Entry(body, textvariable=y_var, width=12).grid(row=5, column=1, sticky="w", pady=(4, 8))

            tk.Label(body, text="Action", bg="#edf4ff", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=6, column=0, sticky="w")
            ttk.Combobox(body, textvariable=action_var, values=tuple(self.CLICK_TYPES.keys()), state="readonly", width=18).grid(row=7, column=0, sticky="w", pady=(4, 8))
            tk.Label(body, text="Delay after step", bg="#edf4ff", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=6, column=1, sticky="w")
            ttk.Entry(body, textvariable=delay_var, width=12).grid(row=7, column=1, sticky="w", pady=(4, 8))

            action_row = tk.Frame(body, bg="#edf4ff")
            action_row.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(4, 0))
            ttk.Button(action_row, text="Add Step", style="Secondary.TButton", command=add_step).grid(row=0, column=0, padx=(0, 8))
            ttk.Button(action_row, text="Add Cursor", style="Secondary.TButton", command=add_cursor_step).grid(row=0, column=1, padx=(0, 8))
            ttk.Button(action_row, text="Import Recording", style="Secondary.TButton", command=import_recording).grid(row=0, column=2, padx=(0, 8))
            ttk.Button(action_row, text="Duplicate", style="Secondary.TButton", command=duplicate_step).grid(row=0, column=3)

            manage_row = tk.Frame(body, bg="#edf4ff")
            manage_row.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            ttk.Button(manage_row, text="Move Up", style="Secondary.TButton", command=lambda: move_step(-1)).grid(row=0, column=0, padx=(0, 8))
            ttk.Button(manage_row, text="Move Down", style="Secondary.TButton", command=lambda: move_step(1)).grid(row=0, column=1, padx=(0, 8))
            ttk.Button(manage_row, text="Delete", style="Secondary.TButton", command=delete_step).grid(row=0, column=2, padx=(0, 8))
            ttk.Button(manage_row, text="Clear", style="Secondary.TButton", command=clear_steps).grid(row=0, column=3)

            file_row = tk.Frame(body, bg="#edf4ff")
            file_row.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            ttk.Button(file_row, text="Save", style="Secondary.TButton", command=save_sequence).grid(row=0, column=0, padx=(0, 8))
            ttk.Button(file_row, text="Load", style="Secondary.TButton", command=load_sequence).grid(row=0, column=1, padx=(0, 8))
            ttk.Button(file_row, text="Run Sequence", style="Accent.TButton", command=run_sequence).grid(row=0, column=2)

            tk.Label(body, textvariable=helper_var, bg="#edf4ff", fg="#475569", font=("Segoe UI", 9), wraplength=620, justify=LEFT).grid(row=11, column=0, columnspan=2, sticky="w", pady=(12, 0))

            render_steps()

        def _toggle_recording(self):
            if not self.is_recording:
                if self.recording_data:
                    replace_existing = messagebox.askyesnocancel(
                        "Recording Studio",
                        "Replace the current recording?\n\nChoose Yes to start fresh, No to append to the existing points.",
                        parent=self,
                    )
                    if replace_existing is None:
                        return
                    if replace_existing:
                        self.recording_data = []

                self.is_recording = True
                self.status_var.set("Recording... Move cursor and press 'R' to capture points. Press Record again to stop.")
                try:
                    self.record_hotkey_handle = keyboard.add_hotkey("r", self._record_point)
                except:
                    self.record_hotkey_handle = None
                self._append_activity("Recording armed on hotkey R.")
            else:
                self.is_recording = False
                try:
                    if self.record_hotkey_handle is not None:
                        keyboard.remove_hotkey(self.record_hotkey_handle)
                except:
                    pass
                self.record_hotkey_handle = None
                self.status_var.set(f"Recording stopped. Captured {len(self.recording_data)} points.")
                self._append_activity(f"Recording stopped with {len(self.recording_data)} captured point(s).")
                self._schedule_workspace_save()

        def _record_point(self):
            if self.is_recording:
                try:
                    x, y = pyautogui.position()
                    self.recording_data.append((x, y))
                    self._set_status_safe(f"Captured ({x}, {y}). Total: {len(self.recording_data)}")
                    if winsound:
                        winsound.Beep(800, 50)
                except:
                    pass

        def _play_recording(self):
            if not self.recording_data:
                messagebox.showinfo("Playback", "No recording found. Record some points first.")
                return
            if self.is_playing:
                return
            if self.worker_thread and self.worker_thread.is_alive():
                self.status_var.set("Stop the active click run before starting playback.")
                return
            
            self.stop_event.clear()
            self.is_playing = True
            threading.Thread(target=self._playback_worker, daemon=True).start()
            self._append_activity(f"{'Playback simulation' if self.dry_run_var.get() else 'Playback'} started for {len(self.recording_data)} recorded point(s).")

        def _playback_worker(self):
            dry_run = bool(self.dry_run_var.get())
            self._set_status_safe(f"{'Simulating playback for' if dry_run else 'Playing back'} {len(self.recording_data)} points...")
            try:
                delay = float(self.delay_var.get())
            except:
                delay = 0.5
            
            for i, (x, y) in enumerate(self.recording_data):
                if self.stop_event.is_set():
                    break
                if not dry_run:
                    pyautogui.click(x=x, y=y)
                    self.session_clicks += 1
                self._set_status_safe(f"{'Playback simulation' if dry_run else 'Playback'}: {i+1}/{len(self.recording_data)}")
                time.sleep(delay)
            
            self.is_playing = False
            if self.stop_event.is_set():
                self._set_status_safe("Playback stopped.")
                self._append_activity("Playback stopped before completion.")
            else:
                self._set_status_safe("Playback simulation finished." if dry_run else "Playback finished.")
                self._append_activity(f"{'Playback simulation' if dry_run else 'Playback'} finished after {len(self.recording_data)} point(s).")
            if self.play_sound_var.get() and winsound:
                winsound.Beep(1200, 200)
            self.stop_event.clear()
            self._schedule_workspace_save()

        def _update_dashboard(self):
            try:
                # Update total session clicks
                self.total_session_clicks_var.set(f"Total Session Clicks: {self.session_clicks}")
                self.recording_summary_var.set(
                    f"Recording: {len(self.recording_data)} point(s) | {'active' if self.is_recording else 'idle'}"
                )
                
                # Update elapsed time
                elapsed = int(time.time() - self.session_start_time)
                hours, remainder = divmod(elapsed, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.session_elapsed_var.set(f"Session Elapsed: {hours:02}:{minutes:02}:{seconds:02}")
                
                self.after(1000, self._update_dashboard)
            except:
                pass

        def _open_recording_studio(self):
            palette = self._theme_palette()
            window = tk.Toplevel(self)
            window.title("Recording Studio")
            window.geometry("720x640+320+190")
            window.resizable(True, True)
            window.attributes("-topmost", True)
            window.configure(bg=palette["alt_bg"])
            try:
                window.iconbitmap(_resource_path("favicon.ico"))
            except:
                pass

            body, _record_canvas = _create_scrollable_shell(window, palette["alt_bg"], min_width=700, padx=16, pady=16)
            body.columnconfigure(0, weight=1)

            summary_var = tk.StringVar(value="")
            helper_var = tk.StringVar(value="Manage recorded points, then use playback or hand them off to the sequence builder.")
            offset_x_var = tk.StringVar(value="0")
            offset_y_var = tk.StringVar(value="0")
            state = {"snapshot": None, "recording_flag": None}

            tk.Label(body, text="Recording Studio", bg=palette["alt_bg"], fg=palette["text"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(
                body,
                text="Capture, refine, offset, reorder, and reuse recorded cursor points without leaving the main app.",
                bg=palette["alt_bg"],
                fg=palette["sub"],
                font=("Segoe UI", 9),
                wraplength=640,
                justify=LEFT,
            ).grid(row=1, column=0, sticky="w", pady=(2, 12))

            list_card = tk.Frame(body, bg=palette["card_bg"], padx=12, pady=12, highlightbackground=palette["border"], highlightthickness=1)
            list_card.grid(row=2, column=0, sticky="ew")
            list_card.columnconfigure(0, weight=1)
            list_frame = tk.Frame(list_card, bg=palette["card_bg"])
            list_frame.grid(row=0, column=0, sticky="ew")
            list_frame.columnconfigure(0, weight=1)
            list_box = Listbox(
                list_frame,
                width=66,
                height=15,
                font=("Segoe UI", 10),
                bg=palette["list_bg"],
                fg=palette["list_fg"],
                selectbackground=palette["select_bg"],
                selectforeground=palette["hero_fg"],
                activestyle="none",
                exportselection=False,
            )
            list_box.grid(row=0, column=0, sticky="ew")
            list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=list_box.yview)
            list_scroll.grid(row=0, column=1, sticky="ns")
            list_box.configure(yscrollcommand=list_scroll.set)

            tk.Label(body, textvariable=summary_var, bg=palette["alt_bg"], fg=palette["accent"], font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=(8, 12))

            def selected_index():
                selection = list_box.curselection()
                return selection[0] if selection else None

            def playback_delay():
                try:
                    return max(0.0, float(self.delay_var.get()))
                except Exception:
                    return 0.5

            def render_points(preferred_index=None):
                snapshot = tuple(self.recording_data)
                if snapshot == state["snapshot"] and self.is_recording == state["recording_flag"]:
                    return

                current_index = selected_index() if preferred_index is None else preferred_index
                list_box.delete(0, END)
                for index, (x_pos, y_pos) in enumerate(self.recording_data, start=1):
                    list_box.insert(END, f"{index}. ({x_pos}, {y_pos})")

                if current_index is not None and 0 <= current_index < len(self.recording_data):
                    list_box.selection_clear(0, END)
                    list_box.selection_set(current_index)
                    list_box.activate(current_index)

                estimated_playback = len(self.recording_data) * playback_delay()
                summary_var.set(
                    f"{len(self.recording_data)} point(s) | recording is {'active' if self.is_recording else 'idle'} | est. playback {estimated_playback:.2f}s"
                )
                state["snapshot"] = snapshot
                state["recording_flag"] = self.is_recording

            def schedule_refresh():
                if not window.winfo_exists():
                    return
                render_points()
                window.after(250, schedule_refresh)

            def capture_cursor_point():
                if not _ensure_dependencies("Recording Studio", ["pyautogui"], parent=window):
                    return
                try:
                    x_pos, y_pos = pyautogui.position()
                except Exception as exc:
                    messagebox.showerror("Capture failed", f"Unable to read the cursor position.\n{exc}", parent=window)
                    return

                self.recording_data.append((int(x_pos), int(y_pos)))
                render_points(len(self.recording_data) - 1)
                helper_var.set(f"Captured point ({x_pos}, {y_pos}).")
                self._append_activity(f"Captured recording point {x_pos}, {y_pos}.")
                self._schedule_workspace_save()

            def use_selected_for_target():
                current_index = selected_index()
                if current_index is None:
                    return
                x_pos, y_pos = self.recording_data[current_index]
                self.target_x_var.set(str(x_pos))
                self.target_y_var.set(str(y_pos))
                helper_var.set(f"Loaded ({x_pos}, {y_pos}) into the main planner.")
                self._append_activity(f"Loaded recording point {x_pos}, {y_pos} into the planner.")

            def undo_last_point():
                if not self.recording_data:
                    return
                removed_point = self.recording_data.pop()
                render_points(len(self.recording_data) - 1 if self.recording_data else None)
                helper_var.set(f"Removed last point {removed_point}.")
                self._append_activity(f"Removed last recording point {removed_point}.")
                self._schedule_workspace_save()

            def delete_selected_point():
                current_index = selected_index()
                if current_index is None:
                    return
                removed_point = self.recording_data.pop(current_index)
                render_points(min(current_index, len(self.recording_data) - 1) if self.recording_data else None)
                helper_var.set(f"Removed point {removed_point}.")
                self._append_activity(f"Removed recording point {removed_point}.")
                self._schedule_workspace_save()

            def duplicate_selected_point():
                current_index = selected_index()
                if current_index is None:
                    return
                self.recording_data.insert(current_index + 1, self.recording_data[current_index])
                render_points(current_index + 1)
                helper_var.set("Duplicated the selected point.")
                self._append_activity("Duplicated a recording point.")
                self._schedule_workspace_save()

            def move_point(offset):
                current_index = selected_index()
                if current_index is None:
                    return
                new_index = current_index + offset
                if new_index < 0 or new_index >= len(self.recording_data):
                    return
                self.recording_data[current_index], self.recording_data[new_index] = self.recording_data[new_index], self.recording_data[current_index]
                render_points(new_index)
                helper_var.set("Moved the selected point.")
                self._append_activity("Reordered recording points.")
                self._schedule_workspace_save()

            def reverse_points():
                if len(self.recording_data) < 2:
                    return
                current_index = selected_index()
                self.recording_data.reverse()
                new_index = None if current_index is None else len(self.recording_data) - 1 - current_index
                render_points(new_index)
                helper_var.set("Reversed the recording order.")
                self._append_activity("Reversed recording order.")
                self._schedule_workspace_save()

            def shift_points(selected_only):
                if not self.recording_data:
                    return
                try:
                    offset_x = int(offset_x_var.get())
                    offset_y = int(offset_y_var.get())
                except ValueError:
                    messagebox.showerror("Invalid offset", "Offset values must be whole numbers.", parent=window)
                    return

                if selected_only:
                    current_index = selected_index()
                    if current_index is None:
                        return
                    point_x, point_y = self.recording_data[current_index]
                    self.recording_data[current_index] = (point_x + offset_x, point_y + offset_y)
                    render_points(current_index)
                    helper_var.set(f"Shifted the selected point by {offset_x}, {offset_y}.")
                    self._append_activity(f"Shifted one recording point by {offset_x}, {offset_y}.")
                else:
                    self.recording_data = [(point_x + offset_x, point_y + offset_y) for point_x, point_y in self.recording_data]
                    render_points(selected_index())
                    helper_var.set(f"Shifted all points by {offset_x}, {offset_y}.")
                    self._append_activity(f"Shifted all recording points by {offset_x}, {offset_y}.")
                self._schedule_workspace_save()

            def clear_points():
                if not self.recording_data:
                    return
                if not messagebox.askyesno("Clear recording", "Remove every recorded point?", parent=window):
                    return
                self.recording_data.clear()
                render_points()
                helper_var.set("Recording cleared.")
                self._append_activity("Cleared all recorded points.")
                self._schedule_workspace_save()

            def save_recording():
                if not self.recording_data:
                    messagebox.showinfo("Recording Studio", "Capture at least one point before saving.", parent=window)
                    return

                file_path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json")],
                    initialfile="autoclicker_recording.json",
                    parent=window,
                )
                if not file_path:
                    return

                try:
                    with open(file_path, "w", encoding="utf-8") as file_handle:
                        json.dump(self.recording_data, file_handle, indent=2)
                except Exception as exc:
                    messagebox.showerror("Save failed", f"Unable to save the recording.\n{exc}", parent=window)
                    return

                helper_var.set(f"Saved {len(self.recording_data)} point(s) to {os.path.basename(file_path)}.")
                self._append_activity(f"Saved recording to {os.path.basename(file_path)}.")

            def load_recording():
                file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], parent=window)
                if not file_path:
                    return

                try:
                    loaded_points = _normalize_recording_points(_load_json_file(file_path), strict=True)
                except Exception as exc:
                    messagebox.showerror("Load failed", f"Unable to load the recording.\n{exc}", parent=window)
                    return

                self.recording_data = loaded_points
                render_points(0 if self.recording_data else None)
                helper_var.set(f"Loaded {len(self.recording_data)} point(s) from {os.path.basename(file_path)}.")
                self._append_activity(f"Loaded recording from {os.path.basename(file_path)}.")
                self._schedule_workspace_save()

            button_grid = tk.Frame(body, bg=palette["alt_bg"])
            button_grid.grid(row=4, column=0, sticky="ew")
            for column in range(2):
                button_grid.columnconfigure(column, weight=1)
            ttk.Button(button_grid, text="Toggle Record", style="Secondary.TButton", command=self._toggle_recording).grid(row=0, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(button_grid, text="Capture Cursor", style="Secondary.TButton", command=capture_cursor_point).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(button_grid, text="Use Selected In Planner", style="Secondary.TButton", command=use_selected_for_target).grid(row=1, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(button_grid, text="Playback Recording", style="Secondary.TButton", command=self._play_recording).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(button_grid, text="Move Up", style="Secondary.TButton", command=lambda: move_point(-1)).grid(row=2, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(button_grid, text="Move Down", style="Secondary.TButton", command=lambda: move_point(1)).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(button_grid, text="Duplicate Selected", style="Secondary.TButton", command=duplicate_selected_point).grid(row=3, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(button_grid, text="Delete Selected", style="Secondary.TButton", command=delete_selected_point).grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(button_grid, text="Reverse Order", style="Secondary.TButton", command=reverse_points).grid(row=4, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(button_grid, text="Undo Last", style="Secondary.TButton", command=undo_last_point).grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

            offset_card = tk.Frame(body, bg=palette["card_bg"], padx=12, pady=12, highlightbackground=palette["border"], highlightthickness=1)
            offset_card.grid(row=5, column=0, sticky="ew", pady=(8, 0))
            offset_card.columnconfigure(1, weight=1)
            tk.Label(offset_card, text="Offset Lab", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
            tk.Label(offset_card, text="Shift X", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(offset_card, textvariable=offset_x_var, width=10).grid(row=1, column=1, sticky="w", pady=(8, 0))
            tk.Label(offset_card, text="Shift Y", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=2, sticky="w", padx=(12, 0), pady=(8, 0))
            ttk.Entry(offset_card, textvariable=offset_y_var, width=10).grid(row=1, column=3, sticky="w", pady=(8, 0))
            ttk.Button(offset_card, text="Apply To Selected", style="Secondary.TButton", command=lambda: shift_points(True)).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            ttk.Button(offset_card, text="Apply To All", style="Secondary.TButton", command=lambda: shift_points(False)).grid(row=2, column=2, columnspan=2, sticky="ew", padx=(8, 0), pady=(10, 0))

            file_grid = tk.Frame(body, bg=palette["alt_bg"])
            file_grid.grid(row=6, column=0, sticky="ew", pady=(8, 0))
            for column in range(2):
                file_grid.columnconfigure(column, weight=1)
            ttk.Button(file_grid, text="Save Recording", style="Secondary.TButton", command=save_recording).grid(row=0, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(file_grid, text="Load Recording", style="Secondary.TButton", command=load_recording).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(file_grid, text="Open Sequence Builder", style="Secondary.TButton", command=self._open_sequence_builder).grid(row=1, column=0, sticky="ew")
            ttk.Button(file_grid, text="Clear All", style="Secondary.TButton", command=clear_points).grid(row=1, column=1, sticky="ew", padx=(8, 0))

            tk.Label(body, textvariable=helper_var, bg=palette["alt_bg"], fg=palette["sub"], font=("Segoe UI", 9), wraplength=640, justify=LEFT).grid(row=7, column=0, sticky="w", pady=(12, 0))

            render_points()
            schedule_refresh()

        def _open_sequence_builder(self):
            if not _ensure_dependencies("Coordinate Sequence", ["pyautogui"], parent=self):
                return

            palette = self._theme_palette()
            window = tk.Toplevel(self)
            window.title("Coordinate Sequence")
            window.geometry("760x680+300+180")
            window.resizable(True, True)
            window.attributes("-topmost", True)
            window.configure(bg=palette["alt_bg"])
            try:
                window.iconbitmap(_resource_path("favicon.ico"))
            except:
                pass

            steps = []
            x_var = tk.StringVar(value=self.target_x_var.get())
            y_var = tk.StringVar(value=self.target_y_var.get())
            action_var = tk.StringVar(value=self.click_mode_var.get())
            delay_var = tk.StringVar(value=self.delay_var.get())
            loop_count_var = tk.StringVar(value="1")
            countdown_var = tk.StringVar(value="0")
            summary_var = tk.StringVar(value="0 step(s) | 0.00s total wait")
            helper_var = tk.StringVar(value="Build, edit, and run a click path with countdown and loop controls.")

            body, _sequence_canvas = _create_scrollable_shell(window, palette["alt_bg"], min_width=740, padx=16, pady=16)
            body.columnconfigure(0, weight=1)

            tk.Label(body, text="Coordinate Sequence Builder", bg=palette["alt_bg"], fg=palette["text"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(
                body,
                text="Build a step-by-step click path, edit selected items, and run full or partial sequences with loop controls.",
                bg=palette["alt_bg"],
                fg=palette["sub"],
                font=("Segoe UI", 9),
                wraplength=680,
                justify=LEFT,
            ).grid(row=1, column=0, sticky="w", pady=(2, 12))

            list_card = tk.Frame(body, bg=palette["card_bg"], padx=12, pady=12, highlightbackground=palette["border"], highlightthickness=1)
            list_card.grid(row=2, column=0, sticky="ew")
            list_card.columnconfigure(0, weight=1)
            list_frame = tk.Frame(list_card, bg=palette["card_bg"])
            list_frame.grid(row=0, column=0, sticky="ew")
            list_frame.columnconfigure(0, weight=1)
            list_box = Listbox(
                list_frame,
                width=68,
                height=15,
                font=("Segoe UI", 10),
                bg=palette["list_bg"],
                fg=palette["list_fg"],
                selectbackground=palette["select_bg"],
                selectforeground=palette["hero_fg"],
                activestyle="none",
                exportselection=False,
            )
            list_box.grid(row=0, column=0, sticky="ew")
            list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=list_box.yview)
            list_scroll.grid(row=0, column=1, sticky="ns")
            list_box.configure(yscrollcommand=list_scroll.set)

            tk.Label(body, textvariable=summary_var, bg=palette["alt_bg"], fg=palette["accent"], font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=(8, 12))

            def normalize_steps(raw_steps):
                return _normalize_sequence_steps(raw_steps, self.CLICK_TYPES)

            def selected_index():
                selection = list_box.curselection()
                return selection[0] if selection else None

            def read_editor_step():
                x_pos = int(x_var.get())
                y_pos = int(y_var.get())
                delay_seconds = float(delay_var.get())
                if delay_seconds < 0:
                    raise ValueError("Delay must be zero or greater.")
                action_name = action_var.get()
                if action_name not in self.CLICK_TYPES:
                    raise ValueError("Choose a valid action.")
                return (x_pos, y_pos, action_name, delay_seconds)

            def update_summary():
                try:
                    loop_count = max(1, int(loop_count_var.get()))
                except Exception:
                    loop_count = 1
                total_wait = sum(step[3] for step in steps)
                summary_var.set(
                    f"{len(steps)} step(s) | {total_wait:.2f}s wait per loop | {total_wait * loop_count:.2f}s across {loop_count} loop(s)"
                )

            def render_steps(selected_step=None):
                list_box.delete(0, END)
                for index, (x_pos, y_pos, action_name, delay_seconds) in enumerate(steps, start=1):
                    list_box.insert(END, f"{index}. {action_name} at ({x_pos}, {y_pos}) then wait {delay_seconds:.2f}s")
                update_summary()
                if selected_step is not None and 0 <= selected_step < len(steps):
                    list_box.selection_clear(0, END)
                    list_box.selection_set(selected_step)
                    list_box.activate(selected_step)

            def load_selected_into_editor(_event=None):
                current_step = selected_index()
                if current_step is None:
                    return
                x_pos, y_pos, action_name, delay_seconds = steps[current_step]
                x_var.set(str(x_pos))
                y_var.set(str(y_pos))
                action_var.set(action_name)
                delay_var.set(f"{delay_seconds:.2f}")
                helper_var.set(f"Loaded step {current_step + 1} into the editor.")

            def add_step():
                try:
                    step = read_editor_step()
                except Exception:
                    messagebox.showerror("Invalid step", "Enter valid X, Y, action, and delay values.", parent=window)
                    return
                steps.append(step)
                render_steps(len(steps) - 1)
                helper_var.set("Step added to the sequence.")

            def update_selected_step():
                current_step = selected_index()
                if current_step is None:
                    return
                try:
                    steps[current_step] = read_editor_step()
                except Exception:
                    messagebox.showerror("Invalid step", "Enter valid X, Y, action, and delay values.", parent=window)
                    return
                render_steps(current_step)
                helper_var.set("Selected step updated from the editor.")

            def add_cursor_step():
                try:
                    current_x, current_y = pyautogui.position()
                    x_var.set(str(current_x))
                    y_var.set(str(current_y))
                    add_step()
                except Exception as exc:
                    messagebox.showerror("Capture failed", f"Unable to read the cursor position.\n{exc}", parent=window)

            def import_recording():
                if not self.recording_data:
                    messagebox.showinfo("Sequence builder", "There is no active recording to import.", parent=window)
                    return
                try:
                    delay_seconds = float(delay_var.get())
                    if delay_seconds < 0:
                        raise ValueError
                except Exception:
                    messagebox.showerror("Invalid delay", "Enter a valid delay before importing recorded points.", parent=window)
                    return
                for x_pos, y_pos in self.recording_data:
                    steps.append((int(x_pos), int(y_pos), action_var.get(), delay_seconds))
                render_steps(len(steps) - 1)
                helper_var.set(f"Imported {len(self.recording_data)} recorded point(s).")

            def duplicate_step():
                current_step = selected_index()
                if current_step is None:
                    return
                steps.insert(current_step + 1, steps[current_step])
                render_steps(current_step + 1)
                helper_var.set("Selected step duplicated.")

            def move_step(offset):
                current_step = selected_index()
                if current_step is None:
                    return
                new_index = current_step + offset
                if new_index < 0 or new_index >= len(steps):
                    return
                steps[current_step], steps[new_index] = steps[new_index], steps[current_step]
                render_steps(new_index)
                helper_var.set("Selected step moved.")

            def reverse_steps():
                if len(steps) < 2:
                    return
                current_step = selected_index()
                steps.reverse()
                new_index = None if current_step is None else len(steps) - 1 - current_step
                render_steps(new_index)
                helper_var.set("Sequence order reversed.")

            def delete_step():
                current_step = selected_index()
                if current_step is None:
                    return
                del steps[current_step]
                render_steps(min(current_step, len(steps) - 1) if steps else None)
                helper_var.set("Selected step removed.")

            def clear_steps():
                if not steps:
                    return
                if not messagebox.askyesno("Clear sequence", "Remove every step from the current sequence?", parent=window):
                    return
                steps.clear()
                render_steps()
                helper_var.set("Sequence cleared.")

            def run_sequence_worker(sequence_copy, loop_count, countdown_seconds, dry_run):
                completed_steps = 0
                previous_failsafe = getattr(pyautogui, "FAILSAFE", True)
                try:
                    pyautogui.FAILSAFE = bool(self.pyautogui_failsafe_var.get())
                    if countdown_seconds > 0:
                        target_time = time.perf_counter() + countdown_seconds
                        last_announced = None
                        while time.perf_counter() < target_time:
                            if self.stop_event.is_set():
                                self.ui_queue.put(("status", "Coordinate sequence cancelled during countdown."))
                                self._append_activity("Sequence cancelled during countdown.")
                                return
                            remaining = max(0, target_time - time.perf_counter())
                            announced_value = int(math.ceil(remaining))
                            if announced_value != last_announced:
                                self.ui_queue.put(("status", f"Sequence starting in {announced_value}s."))
                                last_announced = announced_value
                            time.sleep(min(0.1, remaining))

                    for loop_index in range(loop_count):
                        for x_pos, y_pos, action_name, delay_seconds in sequence_copy:
                            if self.stop_event.is_set():
                                self.ui_queue.put(("status", f"Coordinate sequence stopped after {completed_steps} step(s)."))
                                self._append_activity(f"Sequence stopped after {completed_steps} step(s).")
                                return
                            button_name, click_count = self.CLICK_TYPES[action_name]
                            if not dry_run:
                                try:
                                    pyautogui.click(x=x_pos, y=y_pos, button=button_name, clicks=click_count, interval=0.02 if click_count > 1 else 0.0)
                                except Exception as exc:
                                    if exc.__class__.__name__ == "FailSafeException":
                                        self.ui_queue.put(("status", f"Corner fail-safe stopped the sequence after {completed_steps} step(s)."))
                                        self._append_activity(f"Corner fail-safe stopped the sequence after {completed_steps} step(s).")
                                    else:
                                        self.ui_queue.put(("status", f"Sequence click error: {exc}"))
                                        self._append_activity(f"Sequence click error: {exc}")
                                    return
                            completed_steps += 1
                            if delay_seconds > 0:
                                wake_at = time.perf_counter() + delay_seconds
                                while time.perf_counter() < wake_at:
                                    if self.stop_event.is_set():
                                        self.ui_queue.put(("status", f"Coordinate sequence stopped after {completed_steps} step(s)."))
                                        self._append_activity(f"Sequence stopped after {completed_steps} step(s).")
                                        return
                                    time.sleep(min(0.02, wake_at - time.perf_counter()))
                        self.ui_queue.put(("status", f"Sequence loop {loop_index + 1}/{loop_count} complete."))
                    self.ui_queue.put(("status", f"{'Dry-run sequence' if dry_run else 'Coordinate sequence'} complete. Ran {completed_steps} step(s)."))
                    self._append_activity(f"{'Dry-run sequence' if dry_run else 'Sequence'} complete. Ran {completed_steps} step(s).")
                except Exception as exc:
                    self.ui_queue.put(("status", f"Sequence error: {exc}"))
                    self._append_activity(f"Sequence error: {exc}")
                finally:
                    try:
                        pyautogui.FAILSAFE = previous_failsafe
                    except Exception:
                        pass
                    self.sequence_thread = None
                    self.stop_event.clear()

            def launch_sequence(start_from_selected=False):
                if not steps:
                    messagebox.showinfo("Sequence builder", "Add at least one step before running the sequence.", parent=window)
                    return
                if self.worker_thread and self.worker_thread.is_alive():
                    messagebox.showinfo("Sequence builder", "Stop the active click run before starting a sequence.", parent=window)
                    return
                if self.sequence_thread and self.sequence_thread.is_alive():
                    messagebox.showinfo("Sequence builder", "A sequence is already running.", parent=window)
                    return
                if self.is_playing:
                    messagebox.showinfo("Sequence builder", "Stop playback before starting a sequence.", parent=window)
                    return

                try:
                    loop_count = int(loop_count_var.get())
                    countdown_seconds = float(countdown_var.get())
                    if loop_count < 1:
                        raise ValueError
                    if countdown_seconds < 0:
                        raise ValueError
                except Exception:
                    messagebox.showerror("Invalid run settings", "Loop count must be at least 1 and countdown must be zero or greater.", parent=window)
                    return

                if start_from_selected:
                    current_step = selected_index()
                    if current_step is None:
                        messagebox.showinfo("Sequence builder", "Choose a step first, then use Run From Selected.", parent=window)
                        return
                    sequence_copy = list(steps[current_step:])
                    start_label = f"from step {current_step + 1}"
                else:
                    sequence_copy = list(steps)
                    start_label = "from the beginning"

                self.stop_event.clear()
                dry_run = bool(self.dry_run_var.get())
                self.status_var.set(
                    f"{'Simulating' if dry_run else 'Running'} coordinate sequence {start_label} with {len(sequence_copy)} step(s)."
                )
                self._append_activity(
                    f"{'Dry-run sequence' if dry_run else 'Sequence'} started {start_label} with {len(sequence_copy)} step(s) across {loop_count} loop(s)."
                )
                self.sequence_thread = threading.Thread(
                    target=run_sequence_worker,
                    args=(sequence_copy, loop_count, countdown_seconds, dry_run),
                    daemon=True,
                )
                self.sequence_thread.start()

            def save_sequence():
                if not steps:
                    messagebox.showinfo("Sequence builder", "Add at least one step before saving.", parent=window)
                    return
                file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], parent=window)
                if not file_path:
                    return
                try:
                    with open(file_path, "w", encoding="utf-8") as file_handle:
                        json.dump(steps, file_handle, indent=2)
                except Exception as exc:
                    messagebox.showerror("Save failed", f"Unable to save the sequence.\n{exc}", parent=window)
                    return
                helper_var.set(f"Sequence saved to {os.path.basename(file_path)}.")

            def load_sequence():
                file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], parent=window)
                if not file_path:
                    return
                try:
                    normalized_steps = normalize_steps(_load_json_file(file_path))
                except Exception as exc:
                    messagebox.showerror("Load failed", f"Unable to load the sequence.\n{exc}", parent=window)
                    return
                steps.clear()
                steps.extend(normalized_steps)
                render_steps(0 if steps else None)
                helper_var.set(f"Loaded {len(steps)} validated step(s).")

            editor_card = tk.Frame(body, bg=palette["card_bg"], padx=12, pady=12, highlightbackground=palette["border"], highlightthickness=1)
            editor_card.grid(row=4, column=0, sticky="ew")
            tk.Label(editor_card, text="Step Editor", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
            tk.Label(editor_card, text="X", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(editor_card, textvariable=x_var, width=12).grid(row=2, column=0, sticky="w", pady=(4, 0))
            tk.Label(editor_card, text="Y", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(8, 0))
            ttk.Entry(editor_card, textvariable=y_var, width=12).grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(4, 0))
            tk.Label(editor_card, text="Action", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=2, sticky="w", padx=(12, 0), pady=(8, 0))
            ttk.Combobox(editor_card, textvariable=action_var, values=tuple(self.CLICK_TYPES.keys()), state="readonly", width=18).grid(row=2, column=2, sticky="w", padx=(12, 0), pady=(4, 0))
            tk.Label(editor_card, text="Delay after step", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=3, sticky="w", padx=(12, 0), pady=(8, 0))
            ttk.Entry(editor_card, textvariable=delay_var, width=12).grid(row=2, column=3, sticky="w", padx=(12, 0), pady=(4, 0))

            action_grid = tk.Frame(body, bg=palette["alt_bg"])
            action_grid.grid(row=5, column=0, sticky="ew", pady=(8, 0))
            for column in range(2):
                action_grid.columnconfigure(column, weight=1)
            ttk.Button(action_grid, text="Add Step", style="Secondary.TButton", command=add_step).grid(row=0, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(action_grid, text="Update Selected", style="Secondary.TButton", command=update_selected_step).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(action_grid, text="Add Cursor", style="Secondary.TButton", command=add_cursor_step).grid(row=1, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(action_grid, text="Import Recording", style="Secondary.TButton", command=import_recording).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(action_grid, text="Load Selected Into Editor", style="Secondary.TButton", command=load_selected_into_editor).grid(row=2, column=0, columnspan=2, sticky="ew")

            manage_grid = tk.Frame(body, bg=palette["alt_bg"])
            manage_grid.grid(row=6, column=0, sticky="ew", pady=(8, 0))
            for column in range(2):
                manage_grid.columnconfigure(column, weight=1)
            ttk.Button(manage_grid, text="Duplicate", style="Secondary.TButton", command=duplicate_step).grid(row=0, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(manage_grid, text="Reverse Order", style="Secondary.TButton", command=reverse_steps).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(manage_grid, text="Move Up", style="Secondary.TButton", command=lambda: move_step(-1)).grid(row=1, column=0, sticky="ew", pady=(0, 8))
            ttk.Button(manage_grid, text="Move Down", style="Secondary.TButton", command=lambda: move_step(1)).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
            ttk.Button(manage_grid, text="Delete", style="Secondary.TButton", command=delete_step).grid(row=2, column=0, sticky="ew")
            ttk.Button(manage_grid, text="Clear", style="Secondary.TButton", command=clear_steps).grid(row=2, column=1, sticky="ew", padx=(8, 0))

            run_card = tk.Frame(body, bg=palette["card_bg"], padx=12, pady=12, highlightbackground=palette["border"], highlightthickness=1)
            run_card.grid(row=7, column=0, sticky="ew", pady=(8, 0))
            tk.Label(run_card, text="Run Options", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
            tk.Label(run_card, text="Loop count", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(run_card, textvariable=loop_count_var, width=12).grid(row=2, column=0, sticky="w", pady=(4, 0))
            tk.Label(run_card, text="Countdown", bg=palette["card_bg"], fg=palette["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(8, 0))
            ttk.Entry(run_card, textvariable=countdown_var, width=12).grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(4, 0))
            ttk.Button(run_card, text="Run Sequence", style="Accent.TButton", command=lambda: launch_sequence(False)).grid(row=2, column=2, sticky="ew", padx=(12, 8), pady=(4, 0))
            ttk.Button(run_card, text="Run From Selected", style="Secondary.TButton", command=lambda: launch_sequence(True)).grid(row=2, column=3, sticky="ew", pady=(4, 0))
            ttk.Button(run_card, text="Save", style="Secondary.TButton", command=save_sequence).grid(row=3, column=2, sticky="ew", padx=(12, 8), pady=(10, 0))
            ttk.Button(run_card, text="Load", style="Secondary.TButton", command=load_sequence).grid(row=3, column=3, sticky="ew", pady=(10, 0))

            tk.Label(body, textvariable=helper_var, bg=palette["alt_bg"], fg=palette["sub"], font=("Segoe UI", 9), wraplength=680, justify=LEFT).grid(row=8, column=0, sticky="w", pady=(12, 0))

            list_box.bind("<Double-Button-1>", load_selected_into_editor)
            loop_count_var.trace_add("write", lambda *_args: update_summary())
            render_steps()

        def _open_mini_control(self):
            mini = tk.Toplevel(self)
            mini.overrideredirect(True)
            mini.attributes("-topmost", True)
            mini.attributes("-alpha", 0.9)
            mini.geometry("140x50+100+100")
            mini.configure(bg="#1e293b")
            
            # Drag logic
            def start_move(event): mini.x = event.x; mini.y = event.y
            def do_move(event):
                x = mini.winfo_x() + (event.x - mini.x)
                y = mini.winfo_y() + (event.y - mini.y)
                mini.geometry(f"+{x}+{y}")
            mini.bind("<Button-1>", start_move)
            mini.bind("<B1-Motion>", do_move)

            frame = tk.Frame(mini, bg="#1e293b", padx=5, pady=5)
            frame.pack(fill="both", expand=True)
            
            btn_start = tk.Button(frame, text="Start", bg="#0f766e", fg="white", font=("Segoe UI", 10, "bold"), bd=0, command=self.startclick, width=6)
            btn_start.pack(side="left", padx=2)
            
            btn_stop = tk.Button(frame, text="Stop", bg="#b91c1c", fg="white", font=("Segoe UI", 10, "bold"), bd=0, command=self.stopclick, width=6)
            btn_stop.pack(side="left", padx=2)
            
            btn_close = tk.Button(frame, text="X", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10, "bold"), bd=0, command=mini.destroy, width=2)
            btn_close.pack(side="right")



        def _setup_tray(self):
            try:
                from PIL import Image
                image = Image.open(_resource_path("favicon.ico"))
                menu = (
                    item('Restore', self._restore_from_tray),
                    item('Start Clicker', self.startclick),
                    item('Stop Clicker', self.stopclick),
                    item('Exit', self.EXITME)
                )
                self.tray_icon = pystray.Icon("autoclicker", image, "AutoClicker", menu)
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
            except:
                pass

        def _restore_from_tray(self, icon=None, item=None):
            if self.tray_icon is not None:
                try:
                    self.tray_icon.stop()
                except:
                    pass
                self.tray_icon = None
            self.deiconify()
            self.lift()
            self._apply_window_preferences()

        def _minimize_to_tray(self):
            self.withdraw()
            if self.tray_icon is None:
                self._setup_tray()

        def EXITME(self):
            self.is_recording = False
            self.stop_event.set()
            try:
                if self.record_hotkey_handle is not None:
                    keyboard.remove_hotkey(self.record_hotkey_handle)
            except:
                pass
            try:
                if self.emergency_hotkey_handle is not None:
                    keyboard.remove_hotkey(self.emergency_hotkey_handle)
            except:
                pass
            if self.tray_icon is not None:
                try:
                    self.tray_icon.stop()
                except:
                    pass
                self.tray_icon = None
            self._persist_workspace_state()
            self.stop_event.set()
            self.destroy()

    your_gui = YourGUI()
    your_gui.mainloop()
    time.sleep(0)

if __name__ == '__main__':
    cli_args = sys.argv[1:]

    if "--state-json" in cli_args or ("--state-summary" in cli_args and "--json" in cli_args):
        print(json.dumps(_collect_state_summary_data(), indent=2, sort_keys=True))
        raise SystemExit(0)
    if "--state-summary" in cli_args:
        print(_build_state_summary_report())
        raise SystemExit(0)
    if "--backup-state" in cli_args:
        backup_target = _argument_value(cli_args, "--backup-state")
        backup_result = _backup_state_files(backup_target)
        if "--json" in cli_args:
            print(json.dumps(backup_result, indent=2, sort_keys=True))
        else:
            print(f"State backup directory: {backup_result['backup_dir']}")
            print(f"Copied files: {backup_result['count']}")
            for copied_file in backup_result["copied_files"]:
                print(f"- {copied_file}")
        raise SystemExit(0)
    if "--validate-recording" in cli_args:
        recording_path = _argument_value(cli_args, "--validate-recording")
        if not recording_path:
            print("--validate-recording requires a JSON file path.", file=sys.stderr)
            raise SystemExit(2)
        try:
            validation_result = _validate_recording_file(recording_path)
        except Exception as exc:
            validation_result = {"valid": False, "type": "recording", "path": recording_path, "error": str(exc)}
            if "--json" not in cli_args:
                print(f"Recording invalid: {exc}", file=sys.stderr)
            else:
                print(json.dumps(validation_result, indent=2, sort_keys=True))
            raise SystemExit(1)
        if "--json" in cli_args:
            print(json.dumps(validation_result, indent=2, sort_keys=True))
        else:
            print(f"Recording valid: {validation_result['points']} point(s).")
        raise SystemExit(0)
    if "--validate-sequence" in cli_args:
        sequence_path = _argument_value(cli_args, "--validate-sequence")
        if not sequence_path:
            print("--validate-sequence requires a JSON file path.", file=sys.stderr)
            raise SystemExit(2)
        try:
            validation_result = _validate_sequence_file(sequence_path)
        except Exception as exc:
            validation_result = {"valid": False, "type": "sequence", "path": sequence_path, "error": str(exc)}
            if "--json" not in cli_args:
                print(f"Sequence invalid: {exc}", file=sys.stderr)
            else:
                print(json.dumps(validation_result, indent=2, sort_keys=True))
            raise SystemExit(1)
        if "--json" in cli_args:
            print(json.dumps(validation_result, indent=2, sort_keys=True))
        else:
            print(
                f"Sequence valid: {validation_result['steps']} step(s), "
                f"{validation_result['total_wait_seconds']:.3f}s total wait."
            )
        raise SystemExit(0)
    if "--validate-profiles" in cli_args or "--profile-import-preview" in cli_args:
        profile_flag = "--profile-import-preview" if "--profile-import-preview" in cli_args else "--validate-profiles"
        profiles_path = _argument_value(cli_args, profile_flag)
        if not profiles_path:
            print(f"{profile_flag} requires a JSON file path.", file=sys.stderr)
            raise SystemExit(2)
        existing_profiles = None
        if profile_flag == "--profile-import-preview":
            existing_profile_path = _state_file_location(PROFILE_FILE_NAME)
            if os.path.exists(existing_profile_path):
                try:
                    loaded_existing_profiles = _load_json_file(existing_profile_path)
                    if isinstance(loaded_existing_profiles, dict):
                        existing_profiles = loaded_existing_profiles
                except Exception:
                    existing_profiles = None
        try:
            validation_result = _validate_profiles_file(
                profiles_path,
                existing_profiles=existing_profiles,
            )
        except Exception as exc:
            validation_result = {
                "valid": False,
                "type": "profiles",
                "path": profiles_path,
                "mode": profile_flag.lstrip("-"),
                "error": str(exc),
            }
            if "--json" in cli_args:
                print(json.dumps(validation_result, indent=2, sort_keys=True))
            else:
                print(f"Profiles invalid: {exc}", file=sys.stderr)
            raise SystemExit(1)
        validation_result["type"] = "profiles"
        validation_result["mode"] = profile_flag.lstrip("-")
        if "--json" in cli_args:
            print(json.dumps(validation_result, indent=2, sort_keys=True))
        else:
            print(
                f"Profiles {'valid' if validation_result['valid'] else 'need attention'}: "
                f"{validation_result['valid_count']} valid, "
                f"{validation_result['invalid_count']} invalid, "
                f"{validation_result['overwrite_count']} overwrite(s)."
            )
            if validation_result["invalid_count"]:
                for invalid_profile in validation_result["invalid_profiles"]:
                    print(f"- {invalid_profile['name']}: {'; '.join(invalid_profile['errors'])}")
        raise SystemExit(0 if validation_result["valid"] else 1)
    if "--health-json" in cli_args or ("--health-check" in cli_args and "--json" in cli_args):
        print(json.dumps(_collect_headless_health_data(), indent=2, sort_keys=True))
        raise SystemExit(0)
    if any(argument in ("--health-check", "--health") for argument in cli_args):
        print(_build_headless_health_report())
        raise SystemExit(0)
    MAINWINDOW_REDESIGNED()



