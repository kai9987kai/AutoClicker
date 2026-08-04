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
import re

IMPORT_ERRORS = {}
APP_VERSION = "V11.0"
APP_STATE_DIR_NAME = "AutoClicker"
PROFILE_FILE_NAME = "autoclicker_profiles.json"
WORKSPACE_FILE_NAME = "autoclicker_workspace.json"
RUN_LOG_FILE_NAME = "autoclicker_runs.log"
STATE_SCHEMA_VERSION = 2
DEFAULT_CLICK_TYPES = {
    "Left Click": ("left", 1),
    "Right Click": ("right", 1),
    "Middle Click": ("middle", 1),
    "Double Left Click": ("left", 2),
    "Double Right Click": ("right", 2),
    "Double Middle Click": ("middle", 2),
}

# Every action the run engine can emit. "click" entries reproduce DEFAULT_CLICK_TYPES exactly,
# so existing profiles, sequences and workspaces keep loading unchanged.
ACTION_REGISTRY = {
    "Left Click": {"kind": "click", "button": "left", "clicks": 1},
    "Right Click": {"kind": "click", "button": "right", "clicks": 1},
    "Middle Click": {"kind": "click", "button": "middle", "clicks": 1},
    "Double Left Click": {"kind": "click", "button": "left", "clicks": 2},
    "Double Right Click": {"kind": "click", "button": "right", "clicks": 2},
    "Double Middle Click": {"kind": "click", "button": "middle", "clicks": 2},
    "Triple Left Click": {"kind": "click", "button": "left", "clicks": 3},
    "Key Press": {"kind": "key", "uses": ("action_key",)},
    "Key Hold": {"kind": "key_hold", "uses": ("action_key", "hold_duration")},
    "Type Text": {"kind": "text", "uses": ("action_text",)},
    "Scroll Up": {"kind": "scroll", "direction": 1, "uses": ("scroll_amount",)},
    "Scroll Down": {"kind": "scroll", "direction": -1, "uses": ("scroll_amount",)},
    "Click And Hold": {"kind": "hold", "button": "left", "uses": ("hold_duration",)},
    "Drag To": {"kind": "drag", "button": "left", "uses": ("drag_to_x", "drag_to_y", "hold_duration")},
    "Move Only": {"kind": "move"},
}
ACTION_DEFAULTS = {
    "action_key": "space",
    "action_text": "",
    "scroll_amount": 3,
    "hold_duration": 0.25,
    "drag_to_x": 0,
    "drag_to_y": 0,
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
    "action_key",
    "action_text",
    "scroll_amount",
    "hold_duration",
    "drag_to_x",
    "drag_to_y",
    "pacing_mode",
    "scheduled_start",
    "target_cps",
}
PROFILE_INT_FIELDS = {
    "target_x",
    "target_y",
    "jitter_x",
    "jitter_y",
    "max_actions",
    "micro_pause_every",
    "repeat_count",
    "scroll_amount",
    "drag_to_x",
    "drag_to_y",
}
PROFILE_FLOAT_FIELDS = {
    "delay",
    "delay_variance",
    "countdown",
    "runtime_limit",
    "micro_pause_duration",
    "window_opacity",
    "ui_scale",
    "hold_duration",
    "target_cps",
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
    "click_mode": set(ACTION_REGISTRY),
    "repeat_mode": {"Infinite", "Burst Count"},
    "behaviour_preset": {"Balanced", "Precision", "Burst Sprint", "Human Mimic", "Feather Touch"},
    "theme": {"Light", "Dark", "Ocean", "Midnight", "System"},
    "pacing_mode": {"Precise", "Legacy V10.1"},
}
# The validator used to warn outside 0.2-1.0 / 0.5-2.0 while the runtime clamped to these
# tighter bounds, so a "valid" profile could still be silently changed on load.
WINDOW_OPACITY_RANGE = (0.70, 1.00)
UI_SCALE_RANGE = (0.90, 1.35)
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
            file_handle.flush()
            try:
                os.fsync(file_handle.fileno())
            except Exception:
                pass
        os.replace(temp_path, path)
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise


def _interruptible_sleep(duration, should_stop=None, slice_seconds=0.02, clock=None, sleeper=None):
    """Sleep up to `duration`, checking `should_stop` between short slices.

    Returns True when the full duration elapsed and False when `should_stop` cut it short.
    Sleep arguments are clamped to >= 0 so a descheduled thread can never hit
    ValueError: sleep length must be non-negative.
    """
    clock = clock or time.perf_counter
    sleeper = sleeper or time.sleep
    try:
        duration = float(duration)
    except Exception:
        return True
    if duration <= 0:
        return not (should_stop is not None and should_stop())

    slice_seconds = max(0.001, float(slice_seconds))
    wake_at = clock() + duration
    while True:
        if should_stop is not None and should_stop():
            return False
        remaining = wake_at - clock()
        if remaining <= 0:
            return True
        sleeper(max(0.0, min(slice_seconds, remaining)))


def _resolve_action(action_name, config=None, registry=None):
    """Describe an action as {kind, callable name, kwargs} without touching pyautogui.

    Keeping dispatch declarative means every action the engine can emit is verifiable
    headlessly, on machines with no display and no pyautogui installed.
    """
    registry = registry if registry is not None else ACTION_REGISTRY
    if action_name not in registry:
        raise ValueError(f"Unknown action type: {action_name!r}")
    spec = registry[action_name]
    config = config or {}

    def setting(name):
        value = config.get(name, ACTION_DEFAULTS.get(name))
        return ACTION_DEFAULTS.get(name) if value is None else value

    kind = spec["kind"]
    x_pos, y_pos = config.get("x", 0), config.get("y", 0)

    if kind == "click":
        return {"kind": kind, "call": "click",
                "kwargs": {"x": x_pos, "y": y_pos, "button": spec["button"], "clicks": spec["clicks"]}}
    if kind == "move":
        return {"kind": kind, "call": "moveTo", "kwargs": {"x": x_pos, "y": y_pos}}
    if kind == "key":
        key_name = str(setting("action_key")).strip()
        if not key_name:
            raise ValueError("Key Press needs a key name (for example: space, enter, f5, a).")
        return {"kind": kind, "call": "press", "kwargs": {"keys": key_name}}
    if kind == "key_hold":
        key_name = str(setting("action_key")).strip()
        if not key_name:
            raise ValueError("Key Hold needs a key name (for example: shift, w, ctrl).")
        return {"kind": kind, "call": "keyDown/keyUp",
                "kwargs": {"key": key_name, "hold_duration": max(0.0, float(setting("hold_duration")))}}
    if kind == "text":
        text_value = str(setting("action_text"))
        if not text_value:
            raise ValueError("Type Text needs some text to type.")
        return {"kind": kind, "call": "write", "kwargs": {"message": text_value}}
    if kind == "scroll":
        magnitude = abs(int(setting("scroll_amount")))
        if magnitude == 0:
            raise ValueError("Scroll amount must not be zero.")
        return {"kind": kind, "call": "scroll",
                "kwargs": {"clicks": magnitude * spec["direction"], "x": x_pos, "y": y_pos}}
    if kind == "hold":
        return {"kind": kind, "call": "mouseDown/mouseUp",
                "kwargs": {"x": x_pos, "y": y_pos, "button": spec["button"],
                           "hold_duration": max(0.0, float(setting("hold_duration")))}}
    if kind == "drag":
        return {"kind": kind, "call": "mouseDown/moveTo/mouseUp",
                "kwargs": {"x": x_pos, "y": y_pos,
                           "to_x": int(setting("drag_to_x")), "to_y": int(setting("drag_to_y")),
                           "button": spec["button"],
                           "hold_duration": max(0.0, float(setting("hold_duration")))}}
    raise ValueError(f"Unsupported action kind: {kind!r}")


def _action_moves_pointer(action_name, registry=None):
    """True when the action is anchored to the target coordinate."""
    registry = registry if registry is not None else ACTION_REGISTRY
    spec = registry.get(action_name) or {}
    return spec.get("kind") not in ("key", "key_hold", "text")


def _cps_to_delay(cps):
    """Convert a clicks-per-second target into a per-action delay in seconds."""
    try:
        cps = float(cps)
    except Exception:
        return None
    if cps <= 0:
        return None
    return 1.0 / cps


def _delay_to_cps(delay):
    """Convert a per-action delay into clicks per second. Zero delay means unbounded."""
    try:
        delay = float(delay)
    except Exception:
        return None
    if delay <= 0:
        return None
    return 1.0 / delay


def _rate_stats(samples, window_seconds=3.0):
    """Summarise (timestamp, cumulative_actions) samples into instant/average/peak rates."""
    points = [(float(t), int(n)) for t, n in (samples or [])]
    if len(points) < 2:
        return {"instant_cps": 0.0, "average_cps": 0.0, "peak_cps": 0.0, "samples": len(points)}

    first_time, first_count = points[0]
    last_time, last_count = points[-1]
    span = last_time - first_time
    average = (last_count - first_count) / span if span > 0 else 0.0

    window_start = last_time - max(0.001, float(window_seconds))
    windowed = [p for p in points if p[0] >= window_start] or points[-2:]
    window_span = windowed[-1][0] - windowed[0][0]
    instant = (windowed[-1][1] - windowed[0][1]) / window_span if window_span > 0 else average

    peak = 0.0
    for (t0, n0), (t1, n1) in zip(points, points[1:]):
        step = t1 - t0
        if step > 0:
            peak = max(peak, (n1 - n0) / step)

    return {
        "instant_cps": round(instant, 3),
        "average_cps": round(average, 3),
        "peak_cps": round(peak, 3),
        "samples": len(points),
    }


def _effective_action_period(delay, pacing_mode="Precise", human_like=False, library_pause=0.1):
    """Predict the real seconds-per-action, including PyAutoGUI's own inter-call pause.

    In Legacy V10.1 mode pyautogui.PAUSE is left at its default, so each emitted call
    silently adds `library_pause`; the UI used to promise the raw delay and be wrong by 2-3x.
    """
    try:
        delay = max(0.0, float(delay))
    except Exception:
        delay = 0.0
    if pacing_mode == "Precise":
        overhead = 0.0
    else:
        overhead = float(library_pause) * (2 if human_like else 1)
    if human_like:
        overhead += 0.03  # average of the 0.01-0.05s humanised moveTo duration
    return delay + overhead


def _validate_hotkey(hotkey, parser=None):
    """Check a hotkey string is one `keyboard` can actually poll.

    `keyboard.is_pressed` raises for multi-step hotkeys ("a, b") and unmapped key names,
    and the engine used to swallow that, leaving a run with a silently inert stop key.
    """
    hotkey = str(hotkey or "").strip()
    if not hotkey:
        return {"valid": False, "hotkey": "", "reason": "No hotkey set."}
    if "," in hotkey:
        return {
            "valid": False,
            "hotkey": hotkey,
            "reason": "Multi-step hotkeys (\"a, b\") cannot be polled; use a combination like ctrl+k.",
        }
    if parser is None:
        parser = globals().get("keyboard")
        parser = getattr(parser, "parse_hotkey", None) if parser else None
    if parser is None:
        return {"valid": True, "hotkey": hotkey, "reason": "Not verified: keyboard support is unavailable."}
    try:
        parser(hotkey)
    except Exception as exc:
        return {"valid": False, "hotkey": hotkey, "reason": f"'{hotkey}' is not a key this system recognises ({exc})."}
    return {"valid": True, "hotkey": hotkey, "reason": f"Stop hotkey is {hotkey}."}


def _clamp_geometry_to_screen(geometry, screen_width, screen_height, margin=80):
    """Keep a restored "WxH+X+Y" geometry on-screen.

    A layout saved on a second monitor used to be restored verbatim, putting the
    window somewhere the user could not reach it.
    """
    text = str(geometry or "").strip()
    match = re.match(r"^(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)$", text)
    if not match:
        return text
    width, height = int(match.group(1)), int(match.group(2))
    x_pos, y_pos = int(match.group(3)), int(match.group(4))

    width = max(200, min(width, int(screen_width)))
    height = max(200, min(height, int(screen_height)))
    x_pos = max(0, min(x_pos, max(0, int(screen_width) - margin)))
    y_pos = max(0, min(y_pos, max(0, int(screen_height) - margin)))
    return f"{width}x{height}+{x_pos}+{y_pos}"


def _detect_system_theme(reader=None):
    """Resolve the OS appearance preference to "Light" or "Dark".

    `reader` lets tests inject a value; on Windows the real source is the
    AppsUseLightTheme registry value under Personalize.
    """
    if reader is not None:
        try:
            return "Dark" if not reader() else "Light"
        except Exception:
            return "Light"
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            apps_use_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "Light" if apps_use_light else "Dark"
    except Exception:
        return "Light"


def _rotate_run_log(log_path, keep=1):
    """Roll `x.log` to `x.log.1` so the live log never grows without bound."""
    try:
        oldest = f"{log_path}.{keep}"
        if os.path.exists(oldest):
            os.remove(oldest)
        for index in range(keep - 1, 0, -1):
            source = f"{log_path}.{index}"
            if os.path.exists(source):
                os.replace(source, f"{log_path}.{index + 1}")
        if os.path.exists(log_path):
            os.replace(log_path, f"{log_path}.1")
        return True
    except Exception:
        return False


def _read_run_log(log_path, limit=200):
    """Read the newest `limit` run records back out of the JSON-lines run log."""
    records = []
    if not log_path or not os.path.exists(log_path):
        return records
    try:
        with open(log_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return records
    return records[-limit:] if limit else records


def _summarize_run_history(records):
    """Aggregate run records into lifetime totals the dashboard can show."""
    records = [r for r in (records or []) if isinstance(r, dict)]
    total_actions = sum(int(r.get("actions", 0) or 0) for r in records)
    total_seconds = sum(float(r.get("elapsed_seconds", 0) or 0) for r in records)
    live = [r for r in records if not r.get("dry_run")]
    reasons = {}
    for record in records:
        reason = str(record.get("stop_reason", "unknown"))
        reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "runs": len(records),
        "live_runs": len(live),
        "dry_runs": len(records) - len(live),
        "actions": total_actions,
        "seconds": round(total_seconds, 3),
        "average_cps": round(total_actions / total_seconds, 3) if total_seconds > 0 else 0.0,
        "stop_reasons": reasons,
        "last_run": records[-1] if records else None,
    }


def _parse_scheduled_start(value, now=None):
    """Resolve a HH:MM / HH:MM:SS wall-clock start into seconds from `now`.

    A time earlier than `now` means tomorrow, so "start at 09:00" set in the evening waits.
    """
    text = str(value or "").strip()
    if not text:
        return {"scheduled": False, "delay_seconds": 0.0, "detail": "No scheduled start."}
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.datetime.strptime(text, fmt)
            break
        except ValueError:
            parsed = None
    if parsed is None:
        return {"scheduled": False, "delay_seconds": 0.0, "error": f"'{text}' is not a HH:MM or HH:MM:SS time."}

    now = now or datetime.datetime.now()
    target = now.replace(hour=parsed.hour, minute=parsed.minute, second=parsed.second, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    delay_seconds = (target - now).total_seconds()
    return {
        "scheduled": True,
        "delay_seconds": round(delay_seconds, 3),
        "start_at": target.isoformat(timespec="seconds"),
        "detail": f"Waiting {_format_seconds(delay_seconds)} until {target.strftime('%H:%M:%S')}.",
    }


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
    pacing_mode = config.get("pacing_mode", "Precise")
    effective_period = _effective_action_period(delay, pacing_mode, config.get("human_like"))
    if delay == 0:
        add("Pace", "review", "Zero delay uses maximum available pace.")
    elif abs(effective_period - delay) > 0.005:
        add(
            "Pace",
            "review",
            f"Base delay is {_format_seconds(delay)} but {pacing_mode} pacing makes each action take "
            f"about {effective_period:.3f}s ({_delay_to_cps(effective_period) or 0:.1f}/sec).",
        )
    else:
        add("Pace", "ok", f"Base delay is {_format_seconds(delay)} (about {_delay_to_cps(delay) or 0:.1f} action(s)/sec).")

    # A hotkey that `keyboard` cannot poll used to be reported green while being inert.
    hotkey_check = _validate_hotkey(config.get("stop_hotkey"))
    if config.get("stop_hotkey"):
        if hotkey_check["valid"]:
            add("Stop hotkey", "ok", hotkey_check["reason"])
        else:
            add("Stop hotkey", "review", hotkey_check["reason"])
    elif repeat_limit is None and runtime_limit == 0 and max_actions == 0:
        add("Stop hotkey", "review", "Continuous run has no stop hotkey.")

    action_name = config.get("click_mode")
    if action_name:
        try:
            _resolve_action(action_name, config)
            add("Action", "ok", f"{action_name} is configured correctly.")
        except Exception as exc:
            add("Action", "review", str(exc))

    schedule = config.get("schedule") or {}
    if schedule.get("error"):
        add("Scheduled start", "review", schedule["error"])
    elif schedule.get("scheduled"):
        add("Scheduled start", "ok", schedule.get("detail", "Scheduled."))

    targets = config.get("targets") or []
    if len(targets) > 1:
        add("Targets", "ok", f"Round-robin cycles {len(targets)} recorded point(s).")

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


DEPENDENCY_CATALOGUE = {
    "pyautogui": {"module": "pyautogui", "required": True, "unlocks": "click, scroll, key and drag output"},
    "keyboard": {"module": "keyboard", "required": True, "unlocks": "stop hotkey, global hotkeys, point recording"},
    "pystray": {"module": "pystray", "required": False, "unlocks": "close-to-tray and the tray menu"},
    "Pillow": {"module": "PIL", "required": False, "unlocks": "Photo Clicker previews and screen sampling"},
    "numpy": {"module": "numpy", "required": False, "unlocks": "fast Colour Clicker region scanning"},
    "opencv-python": {"module": "cv2", "required": False, "unlocks": "Photo Clicker confidence matching"},
    "win10toast": {"module": "win10toast", "required": False, "unlocks": "Windows toast notifications"},
}


def _collect_dependency_health(catalogue=None):
    """Resolve every catalogued dependency to an availability record. Pure and headless."""
    import importlib.util

    catalogue = catalogue if catalogue is not None else DEPENDENCY_CATALOGUE
    dependencies = {}
    for dependency_name, spec in catalogue.items():
        module_name = spec["module"]
        if dependency_name in IMPORT_ERRORS:
            available, detail = False, IMPORT_ERRORS[dependency_name]
        else:
            try:
                found = importlib.util.find_spec(module_name) is not None
            except Exception as exc:
                found, detail = False, f"probe failed: {exc}"
            else:
                detail = "available" if found else "module not found"
            available = found
        dependencies[dependency_name] = {
            "available": available,
            "detail": detail,
            "required": bool(spec.get("required")),
            "unlocks": spec.get("unlocks", ""),
        }
    return dependencies


def _missing_required_dependencies(dependencies):
    """Names of required dependencies that are unavailable, sorted for stable output."""
    return sorted(
        name
        for name, data in (dependencies or {}).items()
        if data.get("required") and not data.get("available")
    )


def _collect_headless_health_data():
    dependencies = _collect_dependency_health()

    profile_file = _state_file_location(PROFILE_FILE_NAME)
    workspace_file = _state_file_location(WORKSPACE_FILE_NAME)
    return {
        "app_version": APP_VERSION,
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "resource_root": os.path.dirname(_resource_path("favicon.ico")),
        "dependencies": dependencies,
        "missing_required": _missing_required_dependencies(dependencies),
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
        tier = "required" if dependency_data.get("required") else "optional"
        if dependency_data["available"]:
            dependency_lines.append(f"- {dependency_name} ({tier}): available")
        else:
            unlocks = dependency_data.get("unlocks") or "extra features"
            dependency_lines.append(
                f"- {dependency_name} ({tier}): missing ({dependency_data['detail']}) - unlocks {unlocks}"
            )
    missing_required = health_data.get("missing_required") or []
    if missing_required:
        dependency_lines.append(f"- ACTION: pip install {' '.join(missing_required)}")

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
    # Defaults to the full action registry so sequences can use keys, scrolls and drags,
    # not just the six original click types.
    click_types = click_types or ACTION_REGISTRY
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
    click_types = click_types or ACTION_REGISTRY
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
        if field_name == "window_opacity" and not WINDOW_OPACITY_RANGE[0] <= value <= WINDOW_OPACITY_RANGE[1]:
            result["warnings"].append(
                f"window_opacity is outside the supported {WINDOW_OPACITY_RANGE[0]:.2f}-"
                f"{WINDOW_OPACITY_RANGE[1]:.2f} range and will be clamped on load"
            )
        if field_name == "ui_scale" and not UI_SCALE_RANGE[0] <= value <= UI_SCALE_RANGE[1]:
            result["warnings"].append(
                f"ui_scale is outside the supported {UI_SCALE_RANGE[0]:.2f}-"
                f"{UI_SCALE_RANGE[1]:.2f} range and will be clamped on load"
            )

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

_WIN10TOAST_CACHE = []


def _load_win10toast():
    """Import win10toast on first use; it drags in pkg_resources and costs ~1s."""
    if _WIN10TOAST_CACHE:
        return _WIN10TOAST_CACHE[0]
    module = None
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*", category=UserWarning)
            import win10toast as _win10toast  # This module only works on Windows.
        module = _win10toast
    except Exception as exc:
        IMPORT_ERRORS.setdefault("win10toast", str(exc))
    _WIN10TOAST_CACHE.append(module)
    return module


################################################################################
#     /\  | |  | |__   __/ __ \   / ____| |    |_   _/ ____| |/ /  ____|  __ \ #
#    /  \ | |  | |  | | | |  | | | |    | |      | || |    | ' /| |__  | |__) |#
#   / /\ \| |  | |  | | | |  | | | |    | |      | || |    |  < |  __| |  _  / #
#  / ____ \ |__| |  | | | |__| | | |____| |____ _| || |____| . \| |____| | \ \ #
# /_/    \_\____/   |_|  \____/   \_____|______|_____\_____|_|\_\______|_|  \_\#
################################################################################

def Photo_Clicker():
    """Public entry point for the upgraded Photo Clicker."""

    if not _ensure_dependencies("Photo Clicker", ["pyautogui", "keyboard"]):
        return
    # Pillow drives the thumbnail preview; without it the window opens with a dead panel.
    if "Pillow" in IMPORT_ERRORS:
        _show_dependency_error("Photo Clicker preview", ["Pillow"])

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
                    elif "confidence" in str(exc).lower() and "opencv" in str(exc).lower():
                        # PyAutoGUI needs OpenCV for confidence matching. Say so plainly
                        # instead of leaking its internal message, and stop the scan
                        # rather than repeating an error that cannot resolve itself.
                        set_status(
                            "Confidence matching needs OpenCV. Install it with: "
                            "pip install opencv-python"
                        )
                        break
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
        except Exception:
            pass
        try:
            if master.winfo_exists():
                master.after(100, pump_ui_queue)
        except Exception:
            pass

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
    """Alias for the Photo Clicker tool, kept for the existing menu entry.

    It used to run its own dependency check before calling Photo_Clicker, which runs the
    same check, so a missing package produced two identical error dialogs.
    """
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
        toaster = _load_win10toast().ToastNotifier()
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
            


                def delete(listbox=None):
                    """Remove the selected coordinate from both the listbox and the model.

                    This used to declare `global things` even though `things` is a closure
                    local, so it always raised NameError: the row vanished from the listbox
                    while Run List kept clicking the deleted coordinate. It also read the
                    row *after* deleting it (so it saw the wrong one) and passed that text
                    through eval(), which executes whatever the X/Y fields contain.
                    """
                    selection = list_box.curselection()
                    if not selection:
                        return
                    index = selection[0]
                    if 0 <= index < len(things):
                        del things[index]
                    list_box.delete(0, END)
                    for entry in things:
                        list_box.insert(END, entry)

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


        def EXITME(self):

            YourGUI.destroy(self)

        def startclick(self):
            x1 = threading.Thread(target=self.do_conversion, daemon=True)
            x1.start() 
        def do_conversion(self):
            """Wrapper that always restores the PyAutoGUI corner fail-safe.

            The branches below set FAILSAFE = False and never put it back, which left the
            corner escape hatch disabled for every window opened afterwards.
            """
            previous_failsafe = getattr(pyautogui, "FAILSAFE", True)
            try:
                self._run_classic_clicks()
            except Exception as exc:
                # Report on the Tk thread; a worker-thread traceback would otherwise be
                # invisible in a windowed build.
                message = str(exc)
                try:
                    self.after(0, lambda: messagebox.showerror("AutoClicker", f"Run stopped: {message}"))
                except Exception:
                    pass
            finally:
                try:
                    pyautogui.FAILSAFE = previous_failsafe
                except Exception:
                    pass

        def _run_classic_clicks(self):
            if self.cmb.get() == "Left Click":
                y = self.inputY.get()
                x = self.inputX.get()
                    
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:
                    
                    messagebox.showerror('Invalid point', 'Invalid point')
                    return
                while running:
                    pyautogui.FAILSAFE = False # disables the fail-safe
                    pyautogui.click(x, y)
                                        
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            return
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
                    return
                        
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
                            return
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
                            return
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
                            return
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
                            return
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
                            return
                    else:
                        pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break

    # This used to sit behind `if __name__ == '__main__'`, so Tools > Old Style GUI
    # silently opened nothing whenever the module was imported rather than run directly.
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


def MAINWINDOW_REDESIGNED():
    if not _ensure_dependencies("AutoClicker Control Center", ["pyautogui", "keyboard"]):
        return
    class YourGUI(tk.Tk):
        CLICK_TYPES = DEFAULT_CLICK_TYPES
        ACTION_TYPES = ACTION_REGISTRY
        DELAY_PRESETS = ("0.00", "0.05", "0.10", "0.25", "0.50")
        CPS_PRESETS = ("2", "5", "10", "20", "50")
        # Build-time colour -> palette role. Resolved once per widget (see _apply_theme).
        BG_ROLE_SENTINELS = {
            "#dbe7f2": "main_bg",
            "#f8fafc": "card_bg",
            "#edf4ff": "alt_bg",
            "#0f172a": "hero_bg",
            "#1e293b": "hero_chip_bg",
            "white": "list_bg",
        }
        FG_ROLE_SENTINELS = {
            "#0f172a": "text",
            "#475569": "sub",
            "white": "hero_fg",
            "#f8fafc": "hero_fg",
            "#cbd5e1": "hero_sub",
            "#334155": "sub",
            "#0f766e": "accent",
        }

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
            # One Event per subsystem. A single shared Event let a finishing worker
            # clear the flag out from under a still-running one, resurrecting a stopped run.
            self.stop_event = threading.Event()
            self.sequence_stop_event = threading.Event()
            self.playback_stop_event = threading.Event()
            self.pause_event = threading.Event()
            self.run_generation = 0
            self.active_run_generation = 0
            self.ui_queue = queue.Queue()
            self.stop_reason = "idle"
            self.hotkey_notified = False
            self.was_minimized_for_run = False
            self.active_run_was_dry_run = False
            self.rate_samples = []
            self.global_hotkey_handles = {}
            self.lifetime_stats = {"runs": 0, "actions": 0, "seconds": 0.0}
            self._theme_roles = {}
            self.profile_undo_stack = []

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

            # V11 additions: richer action vocabulary, pacing, scheduling and telemetry.
            self.action_key_var = tk.StringVar(value=ACTION_DEFAULTS["action_key"])
            self.action_text_var = tk.StringVar(value=ACTION_DEFAULTS["action_text"])
            self.scroll_amount_var = tk.StringVar(value=str(ACTION_DEFAULTS["scroll_amount"]))
            self.hold_duration_var = tk.StringVar(value=f"{ACTION_DEFAULTS['hold_duration']:.2f}")
            self.drag_to_x_var = tk.StringVar(value="0")
            self.drag_to_y_var = tk.StringVar(value="0")
            self.pacing_mode_var = tk.StringVar(value="Precise")
            self.scheduled_start_var = tk.StringVar(value="")
            self.target_cps_var = tk.StringVar(value="")
            self.round_robin_var = tk.BooleanVar(value=False)
            self.global_hotkeys_var = tk.BooleanVar(value=False)
            self.start_hotkey_var = tk.StringVar(value="ctrl+shift+s")
            self.pause_hotkey_var = tk.StringVar(value="ctrl+shift+p")
            self.capture_hotkey_var = tk.StringVar(value="ctrl+shift+c")
            self.live_rate_var = tk.StringVar(value="Rate: idle")
            self.lifetime_stats_var = tk.StringVar(value="Lifetime: 0 run(s) | 0 action(s) | 0.00s")
            self.action_params_var = tk.StringVar(value="")
            self.hotkey_status_var = tk.StringVar(value="Global hotkeys are off.")

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
            # Snapshot each widget's build-time colour role while the tree is still in its
            # authored Light palette; _apply_theme then maps roles, never live colours.
            self._capture_theme_roles()
            self._load_profiles_from_disk()
            self._load_workspace_from_disk()
            self._apply_window_preferences()
            self._update_repeat_state()
            self._update_plan_summary()
            self._append_activity("Control Center ready.")

            self.bind("<Button-3>", self._show_context_menu)
            # Enter used to be bound on the root, so pressing it in any entry field launched a
            # live uncapped run and immediately minimised the window. It is now scoped to Start.
            self.bind("<F5>", lambda _event: self.startclick())
            self.bind("<F6>", lambda _event: self.toggle_pause())
            self.bind("<Escape>", lambda _event: self.stopclick())
            self.protocol("WM_DELETE_WINDOW", self._handle_close_request)
            self.after(100, self._pump_ui_queue)
            self.after(200, self._refresh_live_cursor)
            self.after(50, self._apply_theme)
            self._refresh_run_buttons()
            self._load_lifetime_stats()

            # Emergency kill-switch. It now persists the workspace before exiting rather than
            # tearing the process down with os._exit and losing every unsaved change.
            try:
                self.emergency_hotkey_handle = keyboard.add_hotkey("ctrl+shift+k", self._emergency_stop)
            except Exception:
                self.emergency_hotkey_handle = None

        def _emergency_stop(self):
            """Halt everything immediately, then save state and quit from the Tk thread."""
            self.pause_event.clear()
            for event in (self.stop_event, self.sequence_stop_event, self.playback_stop_event):
                event.set()
            self.stop_reason = "emergency"
            try:
                self.after(0, self._emergency_finalize)
            except Exception:
                os._exit(0)

        def _emergency_finalize(self):
            try:
                self._append_activity("Emergency stop hotkey used.")
                self._persist_workspace_state()
            except Exception:
                pass
            try:
                self.EXITME()
            except Exception:
                os._exit(0)

        def _load_lifetime_stats(self):
            """Seed lifetime totals from the on-disk run log so they survive restarts."""
            try:
                summary = _summarize_run_history(_read_run_log(_state_file_location(RUN_LOG_FILE_NAME)))
                self.lifetime_stats = {
                    "runs": summary["runs"],
                    "actions": summary["actions"],
                    "seconds": summary["seconds"],
                }
            except Exception:
                pass

        def _register_global_hotkeys(self):
            """Bind start / pause / stop / capture to system-wide hotkeys."""
            self._unregister_global_hotkeys()
            if keyboard is None:
                self.hotkey_status_var.set("Global hotkeys need the 'keyboard' package.")
                return
            bindings = {
                "start": (self.start_hotkey_var.get().strip(), lambda: self.after(0, self.startclick)),
                "pause": (self.pause_hotkey_var.get().strip(), lambda: self.after(0, self.toggle_pause)),
                "capture": (self.capture_hotkey_var.get().strip(), lambda: self.after(0, self._capture_cursor_position)),
            }
            registered, problems = [], []
            for name, (hotkey, callback) in bindings.items():
                if not hotkey:
                    continue
                check = _validate_hotkey(hotkey)
                if not check["valid"]:
                    problems.append(f"{name}: {check['reason']}")
                    continue
                try:
                    self.global_hotkey_handles[name] = keyboard.add_hotkey(hotkey, callback)
                    registered.append(f"{name}={hotkey}")
                except Exception as exc:
                    problems.append(f"{name}: {exc}")

            if registered and not problems:
                self.hotkey_status_var.set("Global hotkeys active: " + ", ".join(registered))
            elif registered:
                self.hotkey_status_var.set("Active: " + ", ".join(registered) + " | Failed: " + "; ".join(problems))
            else:
                self.hotkey_status_var.set("No global hotkeys registered. " + "; ".join(problems))
            self._append_activity(self.hotkey_status_var.get())

        def _unregister_global_hotkeys(self):
            for handle in list(self.global_hotkey_handles.values()):
                try:
                    keyboard.remove_hotkey(handle)
                except Exception:
                    pass
            self.global_hotkey_handles = {}

        def _toggle_global_hotkeys(self):
            if self.global_hotkeys_var.get():
                self._register_global_hotkeys()
            else:
                self._unregister_global_hotkeys()
                self.hotkey_status_var.set("Global hotkeys are off.")
            self._schedule_workspace_save()

        def _apply_target_cps(self):
            """Convert the clicks-per-second box into the delay the engine actually uses."""
            delay = _cps_to_delay(self.target_cps_var.get())
            if delay is None:
                messagebox.showerror("Target rate", "Enter a clicks-per-second value greater than zero.", parent=self)
                return
            self.delay_var.set(f"{delay:.4f}".rstrip("0").rstrip(".") or "0")
            self.status_var.set(f"Delay set to {delay:.4f}s for {float(self.target_cps_var.get()):.2f} action(s)/sec.")
            self._update_plan_summary()

        def _sync_cps_from_delay(self):
            cps = _delay_to_cps(self.delay_var.get())
            self.target_cps_var.set("" if cps is None else f"{cps:.2f}")

        def _refresh_action_params(self, *_args):
            """Tell the user which Action Setup fields the selected action actually reads."""
            action_name = self.click_mode_var.get()
            spec = ACTION_REGISTRY.get(action_name)
            if not spec:
                self.action_params_var.set("")
                return
            labels = {
                "action_key": "Key name",
                "action_text": "Text to type",
                "scroll_amount": "Scroll notches",
                "hold_duration": "Hold seconds",
                "drag_to_x": "Drag to X",
                "drag_to_y": "Drag to Y",
            }
            uses = [labels.get(name, name) for name in spec.get("uses", ())]
            if uses:
                self.action_params_var.set(f"{action_name} uses: {', '.join(uses)} (see Action Setup).")
            elif spec["kind"] == "click":
                self.action_params_var.set(f"{action_name} sends {spec['clicks']} {spec['button']} click(s) at the target.")
            else:
                self.action_params_var.set(f"{action_name} needs no extra parameters.")

        def _capture_drag_target(self):
            try:
                x_pos, y_pos = pyautogui.position()
            except Exception as exc:
                self.status_var.set(f"Unable to read the cursor position: {exc}")
                return
            self.drag_to_x_var.set(str(int(x_pos)))
            self.drag_to_y_var.set(str(int(y_pos)))
            self.status_var.set(f"Drag target set to {int(x_pos)}, {int(y_pos)}.")

        def _open_run_history(self):
            """Browse the persistent run log with lifetime totals."""
            palette = self._theme_palette()
            window = tk.Toplevel(self)
            window.title("Run History")
            window.geometry("760x560+300+170")
            window.minsize(560, 420)
            window.attributes("-topmost", True)
            window.configure(bg=palette["card_bg"])
            try:
                window.iconbitmap(_resource_path("favicon.ico"))
            except Exception:
                pass

            window.columnconfigure(0, weight=1)
            window.rowconfigure(1, weight=1)

            summary_var = tk.StringVar(value="")
            tk.Label(window, textvariable=summary_var, bg=palette["card_bg"], fg=palette["text"],
                     font=("Segoe UI", 10, "bold"), wraplength=700, justify=LEFT).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

            text_frame = tk.Frame(window, bg=palette["card_bg"])
            text_frame.grid(row=1, column=0, sticky="nsew", padx=16)
            text_frame.columnconfigure(0, weight=1)
            text_frame.rowconfigure(0, weight=1)
            history_text = tk.Text(text_frame, wrap="none", bg=palette["list_bg"], fg=palette["list_fg"],
                                   font=("Consolas", 9), relief="flat")
            history_text.grid(row=0, column=0, sticky="nsew")
            scroll = ttk.Scrollbar(text_frame, orient="vertical", command=history_text.yview)
            scroll.grid(row=0, column=1, sticky="ns")
            history_text.configure(yscrollcommand=scroll.set)

            def refresh():
                log_path = _state_file_location(RUN_LOG_FILE_NAME)
                records = _read_run_log(log_path)
                summary = _summarize_run_history(records)
                summary_var.set(
                    f"{summary['runs']} run(s) logged ({summary['live_runs']} live, {summary['dry_runs']} dry) | "
                    f"{summary['actions']} action(s) | {_format_seconds(summary['seconds'])} | "
                    f"{summary['average_cps']:.2f} action(s)/sec average"
                )
                lines = [f"Log file: {log_path}", ""]
                if not records:
                    lines.append("No runs recorded yet. Finish a run and it will appear here.")
                for record in reversed(records):
                    lines.append(
                        f"{record.get('finished_at', '?'):<20} "
                        f"{'DRY ' if record.get('dry_run') else 'LIVE'} "
                        f"{str(record.get('click_mode', '?')):<20} "
                        f"{record.get('actions', 0):>8} action(s)  "
                        f"{float(record.get('elapsed_seconds', 0) or 0):>9.2f}s  "
                        f"{record.get('stop_reason', '?')}"
                    )
                history_text.configure(state="normal")
                history_text.delete("1.0", END)
                history_text.insert("1.0", "\n".join(lines))
                history_text.configure(state="disabled")

            def export_history():
                export_path = filedialog.asksaveasfilename(
                    defaultextension=".json", filetypes=[("JSON files", "*.json")], parent=window,
                    initialfile=f"autoclicker-run-history-{datetime.datetime.now():%Y%m%d-%H%M%S}.json",
                )
                if not export_path:
                    return
                records = _read_run_log(_state_file_location(RUN_LOG_FILE_NAME))
                try:
                    _atomic_write_json(export_path, {
                        "app_version": APP_VERSION,
                        "schema_version": STATE_SCHEMA_VERSION,
                        "summary": _summarize_run_history(records),
                        "runs": records,
                    }, sort_keys=True)
                except Exception as exc:
                    messagebox.showerror("Export failed", f"Unable to export run history.\n{exc}", parent=window)
                    return
                self._append_activity(f"Run history exported to {os.path.basename(export_path)}.")
                messagebox.showinfo("Run history", f"Exported to:\n{export_path}", parent=window)

            def clear_history():
                if not messagebox.askyesno("Run history", "Archive the current run log and start a fresh one?", parent=window):
                    return
                log_path = _state_file_location(RUN_LOG_FILE_NAME)
                if _rotate_run_log(log_path):
                    self.lifetime_stats = {"runs": 0, "actions": 0, "seconds": 0.0}
                    self._append_activity("Run history archived.")
                    refresh()
                else:
                    messagebox.showerror("Run history", "Unable to archive the run log.", parent=window)

            button_row = tk.Frame(window, bg=palette["card_bg"])
            button_row.grid(row=2, column=0, sticky="ew", padx=16, pady=16)
            for index in range(4):
                button_row.columnconfigure(index, weight=1)
            ttk.Button(button_row, text="Refresh", style="Secondary.TButton", command=refresh).grid(row=0, column=0, sticky="ew")
            ttk.Button(button_row, text="Export JSON", style="Secondary.TButton", command=export_history).grid(row=0, column=1, sticky="ew", padx=(8, 0))
            ttk.Button(button_row, text="Archive Log", style="Secondary.TButton", command=clear_history).grid(row=0, column=2, sticky="ew", padx=(8, 0))
            ttk.Button(button_row, text="Close", style="Secondary.TButton", command=window.destroy).grid(row=0, column=3, sticky="ew", padx=(8, 0))

            refresh()

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
            theme_name = self.theme_var.get()
            if theme_name == "System":
                theme_name = _detect_system_theme()
            if theme_name == "Midnight":
                return {
                    "main_bg": "#08070f",
                    "card_bg": "#15131f",
                    "alt_bg": "#100e1a",
                    "hero_bg": "#050410",
                    "hero_chip_bg": "#221f33",
                    "hero_fg": "#f8fafc",
                    "hero_sub": "#cbd5e1",
                    "text": "#f8fafc",
                    "sub": "#cbd5e1",
                    "accent": "#a78bfa",
                    "accent_active": "#7c3aed",
                    "danger": "#fb7185",
                    "danger_active": "#e11d48",
                    "secondary_bg": "#2a2740",
                    "secondary_active": "#3b3757",
                    "secondary_fg": "#ede9fe",
                    "chip_bg": "#15131f",
                    "chip_fg": "#c4b5fd",
                    "chip_active": "#221f33",
                    "border": "#3b3757",
                    "status_bg": "#050410",
                    "status_fg": "#ddd6fe",
                    "list_bg": "#100e1a",
                    "list_fg": "#f8fafc",
                    "select_bg": "#7c3aed",
                }
            if theme_name == "Dark":
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
            if theme_name == "Ocean":
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
                "Feather Touch": "Very slow, single clean action per second for fragile or laggy UIs.",
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
                "Feather Touch": {
                    "delay": "1.00",
                    "delay_variance": "0.10",
                    "jitter_x": "0",
                    "jitter_y": "0",
                    "human_like": True,
                    "micro_pause_every": "0",
                    "micro_pause_duration": "0.00",
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
            self.start_button.bind("<Return>", lambda _event: self.startclick())
            self.pause_button = ttk.Button(command_strip, text="Pause", style="Secondary.TButton", command=self.toggle_pause, state=DISABLED)
            self.pause_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
            self.stop_button = ttk.Button(command_strip, text="Stop", style="Danger.TButton", command=self.stopclick, state=DISABLED)
            self.stop_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))
            ttk.Button(command_strip, text="Capture Cursor", style="Secondary.TButton", command=self._capture_cursor_position).grid(row=0, column=3, sticky="ew", padx=(8, 0))
            ttk.Button(command_strip, text="Validate Plan", style="Secondary.TButton", command=self._validate_current_plan).grid(row=0, column=4, sticky="ew", padx=(8, 0))
            ttk.Checkbutton(command_strip, text="Dry Run", variable=self.dry_run_var, style="Command.TCheckbutton").grid(row=0, column=5, sticky="w", padx=(12, 0))
            ttk.Checkbutton(command_strip, text="Fail-safe", variable=self.pyautogui_failsafe_var, style="Command.TCheckbutton").grid(row=0, column=6, sticky="w", padx=(12, 0))
            ttk.Button(command_strip, text="Window Settings", style="Secondary.TButton", command=self._open_settings_window).grid(row=0, column=7, sticky="ew", padx=(8, 0))
            ttk.Button(command_strip, text="Expand All", style="Secondary.TButton", command=self._expand_all_sections).grid(row=1, column=0, sticky="ew", pady=(8, 0))
            ttk.Button(command_strip, text="Collapse Extras", style="Secondary.TButton", command=self._collapse_all_sections).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
            self.command_preset_combo = ttk.Combobox(command_strip, textvariable=self.behaviour_preset_var, values=tuple(sorted(PROFILE_ENUM_FIELDS["behaviour_preset"])), state="readonly")
            self.command_preset_combo.grid(row=1, column=2, columnspan=2, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="Apply Preset", style="Secondary.TButton", command=self._apply_behaviour_preset).grid(row=1, column=4, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="Safety Guard", style="Secondary.TButton", command=lambda: self._set_dropdown_state("safety_guard", True)).grid(row=1, column=5, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="Health Check", style="Secondary.TButton", command=self._open_health_dashboard).grid(row=1, column=6, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="Run History", style="Secondary.TButton", command=self._open_run_history).grid(row=1, column=7, sticky="ew", padx=(8, 0), pady=(8, 0))
            ttk.Button(command_strip, text="Session Report", style="Secondary.TButton", command=self._export_session_report).grid(row=2, column=0, sticky="ew", pady=(8, 0))
            ttk.Button(command_strip, text="State Folder", style="Secondary.TButton", command=self._open_state_folder).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
            tk.Label(command_strip, textvariable=self.live_rate_var, bg="#edf4ff", fg="#0f766e", font=("Segoe UI", 10, "bold")).grid(row=2, column=2, columnspan=3, sticky="w", padx=(12, 0), pady=(8, 0))
            tk.Label(command_strip, textvariable=self.lifetime_stats_var, bg="#edf4ff", fg="#475569", font=("Segoe UI", 9)).grid(row=2, column=5, columnspan=3, sticky="w", padx=(12, 0), pady=(8, 0))
            tk.Label(command_strip, textvariable=self.safety_status_var, bg="#edf4ff", fg="#334155", font=("Segoe UI", 9, "bold"), wraplength=1030, justify=LEFT).grid(row=3, column=0, columnspan=8, sticky="w", pady=(10, 0))
            tk.Label(command_strip, textvariable=self.preset_summary_var, bg="#edf4ff", fg="#0f766e", font=("Segoe UI", 9, "bold"), wraplength=1030, justify=LEFT).grid(row=4, column=0, columnspan=8, sticky="w", pady=(4, 0))

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

            tk.Label(quick_body, text="Action type", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
            self.click_type_combo = ttk.Combobox(quick_body, textvariable=self.click_mode_var, values=tuple(ACTION_REGISTRY.keys()), state="readonly")
            self.click_type_combo.grid(row=2, column=1, sticky="ew", pady=(0, 6))
            self.click_type_combo.bind("<<ComboboxSelected>>", self._refresh_action_params)
            tk.Label(quick_body, text="Repeat mode", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            self.repeat_mode_combo = ttk.Combobox(quick_body, textvariable=self.repeat_mode_var, values=("Infinite", "Burst Count"), state="readonly")
            self.repeat_mode_combo.grid(row=2, column=3, sticky="ew", pady=(0, 6))

            tk.Label(quick_body, text="Burst count", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 6))
            self.repeat_count_entry = ttk.Entry(quick_body, textvariable=self.repeat_count_var)
            self.repeat_count_entry.grid(row=3, column=1, sticky="ew", pady=(0, 6))
            tk.Label(quick_body, text="Stop hotkey", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=3, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(quick_body, textvariable=self.stop_hotkey_var).grid(row=3, column=3, sticky="ew", pady=(0, 6))
            tk.Label(quick_body, textvariable=self.action_params_var, bg="#f8fafc", fg="#0f766e", font=("Segoe UI", 9), wraplength=560, justify=LEFT).grid(row=4, column=0, columnspan=4, sticky="w", pady=(2, 0))

            action_card, action_body = self._create_dropdown_section(
                left_stack,
                "action_setup",
                "Action Setup",
                "Parameters for keyboard, scroll, hold and drag actions.",
            )
            action_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
            action_body.columnconfigure(1, weight=1)
            action_body.columnconfigure(3, weight=1)

            tk.Label(action_body, text="Key name", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(action_body, textvariable=self.action_key_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
            tk.Label(action_body, text="Hold seconds", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(action_body, textvariable=self.hold_duration_var).grid(row=0, column=3, sticky="ew", pady=(0, 6))

            tk.Label(action_body, text="Text to type", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(action_body, textvariable=self.action_text_var).grid(row=1, column=1, columnspan=3, sticky="ew", pady=(0, 6))

            tk.Label(action_body, text="Scroll notches", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(action_body, textvariable=self.scroll_amount_var).grid(row=2, column=1, sticky="ew", pady=(0, 6))
            tk.Label(action_body, text="Drag to X / Y", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=2, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            drag_row = tk.Frame(action_body, bg="#f8fafc")
            drag_row.grid(row=2, column=3, sticky="ew", pady=(0, 6))
            drag_row.columnconfigure(0, weight=1)
            drag_row.columnconfigure(1, weight=1)
            ttk.Entry(drag_row, textvariable=self.drag_to_x_var, width=8).grid(row=0, column=0, sticky="ew")
            ttk.Entry(drag_row, textvariable=self.drag_to_y_var, width=8).grid(row=0, column=1, sticky="ew", padx=(6, 0))

            ttk.Button(action_body, text="Use Cursor As Drag Target", style="Secondary.TButton", command=self._capture_drag_target).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 6))
            ttk.Checkbutton(action_body, text="Cycle recorded points (round-robin)", variable=self.round_robin_var, style="App.TCheckbutton").grid(row=3, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(0, 6))

            timing_card, timing_body = self._create_dropdown_section(
                left_stack,
                "timing",
                "Timing and Repeat",
                "Delay, countdown, runtime cap, and other rhythm controls live here.",
            )
            timing_card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
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

            tk.Label(timing_body, text="Target actions/sec", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(timing_body, textvariable=self.target_cps_var).grid(row=3, column=1, sticky="ew", pady=(0, 6))
            cps_row = tk.Frame(timing_body, bg="#f8fafc")
            cps_row.grid(row=3, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Button(cps_row, text="Apply Rate", style="Secondary.TButton", command=self._apply_target_cps).grid(row=0, column=0)
            ttk.Button(cps_row, text="Read From Delay", style="Secondary.TButton", command=self._sync_cps_from_delay).grid(row=0, column=1, padx=(6, 0))
            cps_preset_bar = tk.Frame(timing_body, bg="#f8fafc")
            cps_preset_bar.grid(row=4, column=1, columnspan=3, sticky="w", pady=(0, 6))
            for index, preset in enumerate(self.CPS_PRESETS):
                ttk.Button(
                    cps_preset_bar, text=f"{preset}/s", style="Chip.TButton",
                    command=lambda value=preset: (self.target_cps_var.set(value), self._apply_target_cps()),
                ).grid(row=0, column=index, padx=(0 if index == 0 else 4, 0))

            tk.Label(timing_body, text="Pacing mode", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=5, column=0, sticky="w", pady=(0, 6))
            ttk.Combobox(timing_body, textvariable=self.pacing_mode_var, values=("Precise", "Legacy V10.1"), state="readonly").grid(row=5, column=1, sticky="ew", pady=(0, 6))
            tk.Label(timing_body, text="Start at (HH:MM)", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=5, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(timing_body, textvariable=self.scheduled_start_var).grid(row=5, column=3, sticky="ew", pady=(0, 6))

            safety_card, safety_body = self._create_dropdown_section(
                left_stack,
                "safety_guard",
                "Safety Guard",
                "Action caps, corner fail-safe behaviour, and plan validation.",
            )
            safety_card.grid(row=3, column=0, sticky="ew", pady=(12, 0))
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
            innovation_card.grid(row=4, column=0, sticky="ew", pady=(12, 0))
            innovation_body.columnconfigure(1, weight=1)
            innovation_body.columnconfigure(3, weight=1)

            tk.Label(innovation_body, text="Behaviour preset", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            self.innovation_preset_combo = ttk.Combobox(innovation_body, textvariable=self.behaviour_preset_var, values=tuple(sorted(PROFILE_ENUM_FIELDS["behaviour_preset"])), state="readonly")
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

            hotkey_card, hotkey_body = self._create_dropdown_section(
                left_stack,
                "hotkey_center",
                "Hotkey Center",
                "System-wide hotkeys so the app is drivable while it is minimised over the target.",
            )
            hotkey_card.grid(row=5, column=0, sticky="ew", pady=(12, 0))
            hotkey_body.columnconfigure(1, weight=1)
            hotkey_body.columnconfigure(3, weight=1)

            tk.Label(hotkey_body, text="Start hotkey", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(hotkey_body, textvariable=self.start_hotkey_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
            tk.Label(hotkey_body, text="Pause hotkey", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Entry(hotkey_body, textvariable=self.pause_hotkey_var).grid(row=0, column=3, sticky="ew", pady=(0, 6))

            tk.Label(hotkey_body, text="Capture hotkey", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(hotkey_body, textvariable=self.capture_hotkey_var).grid(row=1, column=1, sticky="ew", pady=(0, 6))
            ttk.Checkbutton(hotkey_body, text="Enable global hotkeys", variable=self.global_hotkeys_var, command=self._toggle_global_hotkeys, style="App.TCheckbutton").grid(row=1, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(0, 6))
            ttk.Button(hotkey_body, text="Re-register Hotkeys", style="Secondary.TButton", command=self._register_global_hotkeys).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 6))
            tk.Label(hotkey_body, text="In-window: F5 start, F6 pause, Esc stop.", bg="#f8fafc", fg="#475569", font=("Segoe UI", 9)).grid(row=2, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(0, 6))
            tk.Label(hotkey_body, textvariable=self.hotkey_status_var, bg="#f8fafc", fg="#0f766e", font=("Segoe UI", 9, "bold"), wraplength=620, justify=LEFT).grid(row=3, column=0, columnspan=4, sticky="w")

            tools_card, tools_body = self._create_dropdown_section(
                left_stack,
                "tools",
                "Tools and Helpers",
                "Open specialist windows only when you need them instead of keeping everything on screen.",
            )
            tools_card.grid(row=6, column=0, sticky="ew", pady=(12, 0))
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
            profiles_card.grid(row=7, column=0, sticky="ew", pady=(12, 0))
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
            self.profile_undo_button = ttk.Button(
                profiles_body, text="Undo Profile Change", style="Secondary.TButton",
                command=self._undo_profile_change, state=DISABLED,
            )
            self.profile_undo_button.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 0))

            window_card, window_body = self._create_dropdown_section(
                left_stack,
                "window_studio",
                "Window Studio",
                "Desktop-focused options, visual tuning, and layout presets stay concealed until needed.",
            )
            window_card.grid(row=8, column=0, sticky="ew", pady=(12, 0))
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
            tk.Label(summary_body, textvariable=self.live_rate_var, bg="#f8fafc", fg="#0f766e", font=("Segoe UI", 9, "bold"), wraplength=360, justify=LEFT).grid(row=16, column=0, sticky="w", pady=(4, 0))
            tk.Label(summary_body, textvariable=self.lifetime_stats_var, bg="#f8fafc", fg="#475569", font=("Segoe UI", 9), wraplength=360, justify=LEFT).grid(row=17, column=0, sticky="w", pady=(4, 0))
            tk.Label(summary_body, text="Preset", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 10, "bold")).grid(row=18, column=0, sticky="w", pady=(12, 0))
            tk.Label(summary_body, textvariable=self.preset_summary_var, bg="#f8fafc", fg="#334155", font=("Segoe UI", 10), wraplength=360, justify=LEFT).grid(row=19, column=0, sticky="w", pady=(4, 0))

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
            # The feed kept 80 entries but only ever showed the last 12, with no scrollbar.
            activity_frame = tk.Frame(controls_body, bg="#f8fafc")
            activity_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 8))
            activity_frame.columnconfigure(0, weight=1)
            activity_frame.rowconfigure(0, weight=1)
            self.activity_list = Listbox(activity_frame, height=10, font=("Segoe UI", 9), bg="white", fg="#0f172a", selectbackground="#1d4ed8", activestyle="none", exportselection=False)
            self.activity_list.grid(row=0, column=0, sticky="nsew")
            activity_scroll = ttk.Scrollbar(activity_frame, orient="vertical", command=self.activity_list.yview)
            activity_scroll.grid(row=0, column=1, sticky="ns")
            self.activity_list.configure(yscrollcommand=activity_scroll.set)
            self.activity_list.bind("<Control-c>", self._copy_activity_selection)
            self.activity_list.bind("<Double-Button-1>", self._copy_activity_selection)

            activity_actions = tk.Frame(controls_body, bg="#f8fafc")
            activity_actions.grid(row=5, column=0, sticky="ew", pady=(0, 8))
            activity_actions.columnconfigure(0, weight=1)
            activity_actions.columnconfigure(1, weight=1)
            ttk.Button(activity_actions, text="Copy Log", style="Secondary.TButton", command=self._copy_activity_log).grid(row=0, column=0, sticky="ew")
            ttk.Button(activity_actions, text="Export Log", style="Secondary.TButton", command=self._export_activity_log).grid(row=0, column=1, sticky="ew", padx=(8, 0))
            ttk.Button(controls_body, text="Exit", style="Secondary.TButton", command=self.EXITME).grid(row=6, column=0, sticky="ew")

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
                self.action_key_var,
                self.action_text_var,
                self.scroll_amount_var,
                self.hold_duration_var,
                self.drag_to_x_var,
                self.drag_to_y_var,
                self.pacing_mode_var,
                self.scheduled_start_var,
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
                self.round_robin_var,
            ):
                variable.trace_add("write", self._handle_state_change)

            self._refresh_action_params()

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
            tools_menu.add_command(label='Start', command=self.startclick, accelerator='F5')
            tools_menu.add_command(label='Pause / Resume', command=self.toggle_pause, accelerator='F6')
            tools_menu.add_command(label='Stop', command=self.stopclick, accelerator='Esc')
            tools_menu.add_separator()
            tools_menu.add_command(label='Find Coordinates', command=self._open_finder)
            tools_menu.add_command(label='Coordinate Sequence', command=self._open_sequence_builder)
            tools_menu.add_command(label='Advanced Colour Clicker', command=Colour_Clicker)
            tools_menu.add_command(label='Locate and Click', command=Locate_Click)
            tools_menu.add_command(label='Photo Clicker', command=Photo_Clicker)
            tools_menu.add_command(label='Auto Clicker Mega Spam', command=self._open_mega_spam)
            tools_menu.add_command(label='Recording Studio', command=self._open_recording_studio)
            tools_menu.add_command(label='Health Check', command=self._open_health_dashboard)
            tools_menu.add_command(label='Run History', command=self._open_run_history)
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
            self.popup.add_command(label='Start', command=self.startclick, accelerator='F5')
            self.popup.add_command(label='Pause / Resume', command=self.toggle_pause, accelerator='F6')
            self.popup.add_command(label='Stop', command=self.stopclick, accelerator='Esc')
            self.popup.add_separator()
            self.popup.add_command(label='Coordinate Sequence', command=self._open_sequence_builder)
            self.popup.add_command(label='Advanced Colour Clicker', command=Colour_Clicker)
            self.popup.add_command(label='Find Coordinates', command=self._open_finder)
            self.popup.add_command(label='Locate and Click', command=Locate_Click)
            self.popup.add_command(label='Photo Clicker', command=Photo_Clicker)
            self.popup.add_command(label='Recording Studio', command=self._open_recording_studio)
            self.popup.add_command(label='Health Check', command=self._open_health_dashboard)
            self.popup.add_command(label='Run History', command=self._open_run_history)
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
            return max(WINDOW_OPACITY_RANGE[0], min(WINDOW_OPACITY_RANGE[1], opacity))

        def _normalize_ui_scale(self):
            try:
                scale = float(self.ui_scale_var.get())
            except Exception:
                scale = 1.0
            return max(UI_SCALE_RANGE[0], min(UI_SCALE_RANGE[1], scale))

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
                "action_key": self.action_key_var.get(),
                "action_text": self.action_text_var.get(),
                "scroll_amount": self.scroll_amount_var.get(),
                "hold_duration": self.hold_duration_var.get(),
                "drag_to_x": self.drag_to_x_var.get(),
                "drag_to_y": self.drag_to_y_var.get(),
                "pacing_mode": self.pacing_mode_var.get(),
                "scheduled_start": self.scheduled_start_var.get(),
                "target_cps": self.target_cps_var.get(),
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
            self.action_key_var.set(str(profile_data.get("action_key", self.action_key_var.get())))
            self.action_text_var.set(str(profile_data.get("action_text", self.action_text_var.get())))
            self.scroll_amount_var.set(str(profile_data.get("scroll_amount", self.scroll_amount_var.get())))
            self.hold_duration_var.set(str(profile_data.get("hold_duration", self.hold_duration_var.get())))
            self.drag_to_x_var.set(str(profile_data.get("drag_to_x", self.drag_to_x_var.get())))
            self.drag_to_y_var.set(str(profile_data.get("drag_to_y", self.drag_to_y_var.get())))
            self.pacing_mode_var.set(profile_data.get("pacing_mode", self.pacing_mode_var.get()))
            self.scheduled_start_var.set(str(profile_data.get("scheduled_start", self.scheduled_start_var.get())))
            self.target_cps_var.set(str(profile_data.get("target_cps", self.target_cps_var.get())))
            self._refresh_preset_summary()
            self._refresh_action_params()
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
                # Show the whole retained history; the scrollbar makes it reachable.
                for log_entry in self.activity_history:
                    self.activity_list.insert(END, log_entry)
                self.activity_list.yview_moveto(1.0)

        def _copy_activity_selection(self, _event=None):
            selection = self.activity_list.curselection()
            if not selection:
                return
            self._copy_to_clipboard(self.activity_list.get(selection[0]), "Activity entry copied.")

        def _copy_activity_log(self):
            if not self.activity_history:
                self.status_var.set("No activity to copy yet.")
                return
            self._copy_to_clipboard(
                "\n".join(self.activity_history),
                f"Copied {len(self.activity_history)} activity line(s) to the clipboard.",
            )

        def _copy_to_clipboard(self, text, message):
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update_idletasks()
                self.status_var.set(message)
            except Exception as exc:
                self.status_var.set(f"Clipboard unavailable: {exc}")

        def _serialize_workspace_state(self):
            geometry = ""
            if self.winfo_exists():
                try:
                    if self.remember_window_geometry_var.get() and self.state() == "normal":
                        geometry = self.geometry()
                except:
                    geometry = ""

            return {
                "schema_version": STATE_SCHEMA_VERSION,
                "app_version": APP_VERSION,
                "profile_data": self._collect_profile_data(),
                "profile_name": self.profile_name_var.get(),
                "profile_choice": self.profile_choice_var.get(),
                "geometry": geometry,
                "recording_data": self.recording_data[-200:],
                "activity_history": self.activity_history[-80:],
                "run_reports": self.run_reports[-40:],
                "round_robin": bool(self.round_robin_var.get()),
                "global_hotkeys": bool(self.global_hotkeys_var.get()),
                "start_hotkey": self.start_hotkey_var.get(),
                "pause_hotkey": self.pause_hotkey_var.get(),
                "capture_hotkey": self.capture_hotkey_var.get(),
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
            if not isinstance(workspace_state, dict):
                self.status_var.set("Workspace file is not a JSON object; keeping defaults.")
                return

            profile_data = workspace_state.get("profile_data")
            if isinstance(profile_data, dict):
                # A malformed persisted profile must not take the whole app down at startup.
                try:
                    self._apply_profile_data(profile_data)
                except Exception as exc:
                    self.status_var.set(f"Saved setup could not be restored ({exc}); defaults kept.")

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

            self.round_robin_var.set(bool(workspace_state.get("round_robin", False)))
            self.start_hotkey_var.set(str(workspace_state.get("start_hotkey", self.start_hotkey_var.get())))
            self.pause_hotkey_var.set(str(workspace_state.get("pause_hotkey", self.pause_hotkey_var.get())))
            self.capture_hotkey_var.set(str(workspace_state.get("capture_hotkey", self.capture_hotkey_var.get())))
            if bool(workspace_state.get("global_hotkeys", False)):
                self.global_hotkeys_var.set(True)
                self._register_global_hotkeys()

            geometry = workspace_state.get("geometry")
            if geometry and self.remember_window_geometry_var.get():
                try:
                    self.geometry(_clamp_geometry_to_screen(str(geometry), self.screen_width, self.screen_height))
                except Exception:
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

            removed_payload = self.saved_profiles[profile_name]
            del self.saved_profiles[profile_name]
            try:
                self._write_profiles_to_disk()
            except Exception as exc:
                # Put it back: the file write failed, so the in-memory set must not diverge.
                self.saved_profiles[profile_name] = removed_payload
                messagebox.showerror("Delete failed", f"Unable to update the profile file.\n{exc}", parent=self)
                return

            self._push_profile_undo("delete", {profile_name: removed_payload})
            self._refresh_profile_choices()
            self._refresh_profile_state()
            self.status_var.set(f"Deleted profile '{profile_name}'. Use Undo Profile Change to restore it.")
            self._append_activity(f"Deleted profile '{profile_name}'.")
            self._schedule_workspace_save()

        def _push_profile_undo(self, label, removed_profiles):
            """Remember the profiles a destructive action removed or overwrote."""
            self.profile_undo_stack.append({
                "label": label,
                "profiles": {name: dict(payload) for name, payload in removed_profiles.items()},
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
            })
            self.profile_undo_stack = self.profile_undo_stack[-10:]
            if hasattr(self, "profile_undo_button"):
                self.profile_undo_button.configure(state=NORMAL)

        def _undo_profile_change(self):
            """Restore the profiles removed or overwritten by the last destructive action."""
            if not self.profile_undo_stack:
                self.status_var.set("Nothing to undo.")
                return
            entry = self.profile_undo_stack.pop()
            restored = list(entry["profiles"])
            previous = {name: self.saved_profiles.get(name) for name in restored}
            self.saved_profiles.update(entry["profiles"])
            try:
                self._write_profiles_to_disk()
            except Exception as exc:
                for name, payload in previous.items():
                    if payload is None:
                        self.saved_profiles.pop(name, None)
                    else:
                        self.saved_profiles[name] = payload
                self.profile_undo_stack.append(entry)
                messagebox.showerror("Undo failed", f"Unable to update the profile file.\n{exc}", parent=self)
                return

            if hasattr(self, "profile_undo_button") and not self.profile_undo_stack:
                self.profile_undo_button.configure(state=DISABLED)
            self._refresh_profile_choices()
            self._refresh_profile_state()
            self.status_var.set(f"Restored {len(restored)} profile(s) from the last {entry['label']}.")
            self._append_activity(f"Undid profile {entry['label']}: restored {', '.join(sorted(restored))}.")
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
                _atomic_write_json(export_path, self.saved_profiles, sort_keys=True)
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
                preview = _preview_profile_import(imported_profiles, self.saved_profiles, self.ACTION_TYPES)
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

            # Snapshot anything about to be overwritten so the import is reversible.
            overwritten = {
                name: dict(self.saved_profiles[name])
                for name in preview["valid_profiles"]
                if name in self.saved_profiles
            }
            self.saved_profiles.update(preview["valid_profiles"])

            try:
                self._write_profiles_to_disk()
            except Exception as exc:
                messagebox.showerror("Import failed", f"Unable to update the local profile file.\n{exc}", parent=self)
                return

            if overwritten:
                self._push_profile_undo("import overwrite", overwritten)
            self._refresh_profile_choices()
            self._refresh_profile_state()
            overwrite_note = f" ({len(overwritten)} overwritten, undoable)" if overwritten else ""
            self.status_var.set(f"Imported {preview['valid_count']} profile(s){overwrite_note}.")
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

            parts = [mode, fail_safe, cap, f"{self.pacing_mode_var.get()} pacing"]
            action_name = self.click_mode_var.get()
            if action_name != "Left Click":
                parts.append(action_name)
            if self.round_robin_var.get() and self.recording_data:
                parts.append(f"round-robin over {len(self.recording_data)} point(s)")
            schedule = _parse_scheduled_start(self.scheduled_start_var.get())
            if schedule.get("error"):
                parts.append("scheduled start invalid")
            elif schedule.get("scheduled"):
                parts.append(f"starts {self.scheduled_start_var.get().strip()}")
            if self.global_hotkeys_var.get():
                parts.append("global hotkeys on")
            self.safety_status_var.set("Safety: " + " | ".join(parts))

        def _format_run_intelligence(self, config):
            planned_actions = config["repeat_limit"]
            if config["max_actions"] > 0:
                if planned_actions is None:
                    planned_actions = config["max_actions"]
                else:
                    planned_actions = min(planned_actions, config["max_actions"])

            # Estimate against the real seconds-per-action, not the raw delay: Legacy
            # pacing adds PyAutoGUI's own inter-call pause and used to double every estimate.
            period = _effective_action_period(
                config["delay"], config.get("pacing_mode", "Precise"), config.get("human_like")
            )
            schedule = config.get("schedule") or {}
            estimated_duration = config["countdown"] + (schedule.get("delay_seconds", 0.0) or 0.0)
            if planned_actions is not None:
                estimated_duration += max(0, planned_actions - 1) * period
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

            measured_rate = _delay_to_cps(period)
            if measured_rate is None:
                pace = "maximum available pace"
            else:
                pace = f"about {measured_rate:.1f} action(s)/sec"

            warnings = []
            if not (0 <= config["x"] < self.screen_width and 0 <= config["y"] < self.screen_height):
                clamped_x = max(0, min(self.screen_width - 1, config["x"]))
                clamped_y = max(0, min(self.screen_height - 1, config["y"]))
                warnings.append(f"target clamps to {clamped_x}, {clamped_y}")
            if config["delay"] == 0:
                warnings.append("zero delay")
            if config.get("pacing_mode") == "Legacy V10.1" and config["delay"] > 0:
                warnings.append(f"legacy pacing: real period {period:.3f}s, not {config['delay']:.3f}s")
            if config["dry_run"]:
                warnings.append("dry run: no clicks will be sent")
            if config["repeat_limit"] is None and config["runtime_limit"] == 0 and config["max_actions"] == 0:
                warnings.append("no runtime/action cap")
            if not config["pyautogui_failsafe"]:
                warnings.append("corner fail-safe off")
            hotkey_check = _validate_hotkey(config.get("stop_hotkey"))
            if config.get("stop_hotkey") and not hotkey_check["valid"]:
                warnings.append("stop hotkey cannot be monitored")
            if schedule.get("scheduled"):
                warnings.append(schedule.get("detail", "scheduled start armed"))

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
            config["targets"] = self._active_target_list(config)
            readiness = _build_readiness_checklist(config, (self.screen_width, self.screen_height))
            self.readiness_var.set(_format_readiness_text(readiness, limit=10))

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
                    try:
                        action, payload = self.ui_queue.get_nowait()
                    except queue.Empty:
                        break
                    try:
                        if action == "status":
                            self.status_var.set(payload)
                        elif action == "progress":
                            count, elapsed, last_point, rates = payload
                            action_label = "simulated action(s)" if self.active_run_was_dry_run else "click action(s)"
                            self.session_var.set(
                                f"Active run: {count} {action_label} processed over {elapsed:.2f} second(s). "
                                f"Last point: {last_point[0]}, {last_point[1]}."
                            )
                            self.live_rate_var.set(
                                f"Rate: {rates['instant_cps']:.2f} now | {rates['average_cps']:.2f} avg | "
                                f"{rates['peak_cps']:.2f} peak action(s)/sec"
                            )
                        elif action == "finished":
                            self._finish_run(*payload)
                        elif action == "refresh_buttons":
                            self._refresh_run_buttons()
                    except Exception as exc:
                        # One malformed message must never kill the pump; without this the
                        # whole UI silently stops updating for the rest of the session.
                        try:
                            self.status_var.set(f"UI update issue: {exc}")
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                if self.winfo_exists():
                    self.after(100, self._pump_ui_queue)
            except Exception:
                pass

        def _build_run_config(self):
            click_mode = self.click_mode_var.get()
            if click_mode not in ACTION_REGISTRY:
                raise ValueError("Choose a valid action type.")

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
            if stop_hotkey:
                hotkey_check = _validate_hotkey(stop_hotkey)
                if not hotkey_check["valid"]:
                    raise ValueError(hotkey_check["reason"])
            if self.repeat_mode_var.get() == "Infinite":
                repeat_limit = None
                if not stop_hotkey:
                    raise ValueError("Set a stop hotkey before starting an infinite run.")
            else:
                repeat_limit = int(self.repeat_count_var.get())
                if repeat_limit < 1:
                    raise ValueError("Burst count must be at least 1.")

            schedule = _parse_scheduled_start(self.scheduled_start_var.get())
            if schedule.get("error"):
                raise ValueError(schedule["error"])

            action_spec = ACTION_REGISTRY[click_mode]
            config = {
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
                "button": action_spec.get("button", "left"),
                "clicks": action_spec.get("clicks", 1),
                "click_mode": click_mode,
                "action_kind": action_spec["kind"],
                "action_key": self.action_key_var.get().strip(),
                "action_text": self.action_text_var.get(),
                "scroll_amount": int(self.scroll_amount_var.get()),
                "hold_duration": float(self.hold_duration_var.get()),
                "drag_to_x": int(self.drag_to_x_var.get()),
                "drag_to_y": int(self.drag_to_y_var.get()),
                "pacing_mode": self.pacing_mode_var.get(),
                "scheduled_start": self.scheduled_start_var.get().strip(),
                "schedule": schedule,
                "behaviour_preset": self.behaviour_preset_var.get(),
                "micro_pause_every": micro_pause_every,
                "micro_pause_duration": micro_pause_duration,
                "human_like": self.human_like_var.get(),
                "dry_run": self.dry_run_var.get(),
                "pyautogui_failsafe": self.pyautogui_failsafe_var.get(),
            }
            # Surfaces bad action parameters (empty key name, zero scroll) before the mouse moves.
            _resolve_action(click_mode, config)
            return config

        def _stop_requested(self, stop_hotkey, stop_event=None):
            stop_event = stop_event if stop_event is not None else self.stop_event
            if stop_event.is_set():
                return True
            if not stop_hotkey or keyboard is None:
                return False

            try:
                pressed = keyboard.is_pressed(stop_hotkey)
            except Exception as exc:
                # A hotkey that cannot be polled is reported once instead of silently
                # leaving the run with no working stop key.
                if not self.hotkey_notified:
                    self.hotkey_notified = True
                    self.ui_queue.put(("status", f"Stop hotkey '{stop_hotkey}' cannot be monitored ({exc}). Use the Stop button."))
                return False

            if pressed:
                self.stop_reason = "hotkey"
                stop_event.set()
                if not self.hotkey_notified:
                    self.hotkey_notified = True
                    self.ui_queue.put(("status", f"Stop hotkey '{stop_hotkey}' pressed. Finishing the current loop."))
                return True
            return False

        def _wait_while_paused(self, config, stop_event=None):
            """Block until Resume or Stop. Returns True if the run should continue."""
            if not self.pause_event.is_set():
                return True
            self.ui_queue.put(("status", "Paused. Press Resume to continue."))
            while self.pause_event.is_set():
                if self._stop_requested(config.get("stop_hotkey"), stop_event):
                    return False
                time.sleep(0.05)
            self.ui_queue.put(("status", "Resumed."))
            return True

        def _emit_action(self, config, point, stop_event=None):
            """Perform one configured action at `point`. No-op when the run is a dry run.

            `stop_event` decides which subsystem's stop token a held key or button honours;
            without it a hold inside a sequence would watch the click run's token instead.
            """
            if config["dry_run"]:
                return
            descriptor = _resolve_action(config["click_mode"], dict(config, x=point[0], y=point[1]))
            kind, kwargs = descriptor["kind"], descriptor["kwargs"]

            if kind == "click":
                pyautogui.click(
                    x=kwargs["x"], y=kwargs["y"], button=kwargs["button"], clicks=kwargs["clicks"],
                    interval=random.uniform(0.01, 0.03) if kwargs["clicks"] > 1 else 0.0,
                )
            elif kind == "move":
                pyautogui.moveTo(kwargs["x"], kwargs["y"])
            elif kind == "key":
                pyautogui.press(kwargs["keys"])
            elif kind == "key_hold":
                pyautogui.keyDown(kwargs["key"])
                try:
                    _interruptible_sleep(kwargs["hold_duration"],
                                         lambda: self._stop_requested(config.get("stop_hotkey"), stop_event))
                finally:
                    pyautogui.keyUp(kwargs["key"])
            elif kind == "text":
                pyautogui.write(kwargs["message"])
            elif kind == "scroll":
                pyautogui.scroll(kwargs["clicks"], x=kwargs["x"], y=kwargs["y"])
            elif kind == "hold":
                pyautogui.mouseDown(x=kwargs["x"], y=kwargs["y"], button=kwargs["button"])
                try:
                    _interruptible_sleep(kwargs["hold_duration"],
                                         lambda: self._stop_requested(config.get("stop_hotkey"), stop_event))
                finally:
                    pyautogui.mouseUp(button=kwargs["button"])
            elif kind == "drag":
                pyautogui.mouseDown(x=kwargs["x"], y=kwargs["y"], button=kwargs["button"])
                try:
                    pyautogui.moveTo(
                        max(0, min(self.screen_width - 1, kwargs["to_x"])),
                        max(0, min(self.screen_height - 1, kwargs["to_y"])),
                        duration=max(0.05, kwargs["hold_duration"]),
                    )
                finally:
                    pyautogui.mouseUp(button=kwargs["button"])

        def _click_worker(self, config):
            previous_failsafe = getattr(pyautogui, "FAILSAFE", True)
            previous_pause = getattr(pyautogui, "PAUSE", 0.1)
            generation = config.get("generation", 0)
            total_actions = 0
            last_click_point = (config["x"], config["y"])
            targets = config.get("targets") or [(config["x"], config["y"])]
            stop_event = self.stop_event
            started_at = time.perf_counter()

            def should_stop():
                return self._stop_requested(config["stop_hotkey"], stop_event)

            def finish(elapsed):
                self.ui_queue.put(("finished", (total_actions, elapsed, last_click_point, generation)))

            try:
                schedule = config.get("schedule") or {}
                if schedule.get("scheduled") and schedule.get("delay_seconds", 0) > 0:
                    self.ui_queue.put(("status", f"Scheduled start armed. {schedule.get('detail', '')}"))
                    if not _interruptible_sleep(schedule["delay_seconds"], should_stop, slice_seconds=0.2):
                        finish(time.perf_counter() - started_at)
                        return

                if config["countdown"] > 0:
                    countdown_deadline = time.perf_counter() + config["countdown"]
                    last_announced = None
                    while True:
                        remaining = countdown_deadline - time.perf_counter()
                        if remaining <= 0:
                            break
                        if should_stop():
                            finish(time.perf_counter() - started_at)
                            return
                        announce_value = int(remaining) + (1 if remaining > int(remaining) else 0)
                        if announce_value != last_announced:
                            self.ui_queue.put(("status", f"Starting in {announce_value}s. Use Stop or {config['stop_hotkey'] or 'manual stop'} to cancel."))
                            last_announced = announce_value
                        _interruptible_sleep(min(0.1, remaining), should_stop, slice_seconds=0.05)

                # The countdown is setup time, not run time: charging it against the runtime
                # cap used to produce silent zero-action runs.
                started_at = time.perf_counter()
                last_progress_update = started_at
                self.rate_samples = [(0.0, 0)]

                try:
                    pyautogui.FAILSAFE = bool(config["pyautogui_failsafe"])
                    if config.get("pacing_mode", "Precise") == "Precise":
                        # PyAutoGUI's default 0.1s inter-call pause otherwise makes the
                        # configured delay a lie by a factor of 2-3.
                        pyautogui.PAUSE = 0
                except Exception:
                    pass

                target_index = 0
                while not should_stop():
                    if not self._wait_while_paused(config, stop_event):
                        break

                    elapsed_before_action = time.perf_counter() - started_at
                    if config["runtime_limit"] > 0 and elapsed_before_action >= config["runtime_limit"]:
                        self.stop_reason = "runtime_limit"
                        break

                    base_x, base_y = targets[target_index % len(targets)]
                    target_index += 1
                    click_x, click_y = base_x, base_y

                    try:
                        if config["human_like"]:
                            if config["jitter_x"] > 0:
                                click_x += int(random.gauss(0, config["jitter_x"] / 2))
                            if config["jitter_y"] > 0:
                                click_y += int(random.gauss(0, config["jitter_y"] / 2))
                            if not config["dry_run"] and _action_moves_pointer(config["click_mode"]):
                                pyautogui.moveTo(
                                    max(0, min(self.screen_width - 1, click_x + random.randint(-2, 2))),
                                    max(0, min(self.screen_height - 1, click_y + random.randint(-2, 2))),
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
                        self._emit_action(config, (click_x, click_y), stop_event)
                    except Exception as exc:
                        if exc.__class__.__name__ == "FailSafeException":
                            self.stop_reason = "failsafe"
                            self.ui_queue.put(("status", "PyAutoGUI corner fail-safe triggered. Run stopped."))
                        else:
                            self.stop_reason = "error"
                            self.ui_queue.put(("status", f"Action error: {exc}"))
                        break

                    total_actions += 1
                    if not config["dry_run"]:
                        self.session_clicks += 1

                    now = time.perf_counter()
                    self.rate_samples.append((now - started_at, total_actions))
                    if len(self.rate_samples) > 400:
                        del self.rate_samples[:-200]
                    if total_actions == 1 or now - last_progress_update >= 0.25:
                        self.ui_queue.put((
                            "progress",
                            (total_actions, now - started_at, last_click_point, _rate_stats(self.rate_samples)),
                        ))
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

                    def runtime_exhausted():
                        return (
                            config["runtime_limit"] > 0
                            and time.perf_counter() - started_at >= config["runtime_limit"]
                        )

                    def wait_gate():
                        if runtime_exhausted():
                            self.stop_reason = "runtime_limit"
                            return True
                        return should_stop()

                    if (
                        config["micro_pause_every"] > 0
                        and config["micro_pause_duration"] > 0
                        and total_actions % config["micro_pause_every"] == 0
                    ):
                        self.ui_queue.put(
                            ("status", f"Micro-pause: resting for {config['micro_pause_duration']:.2f}s after {total_actions} action(s).")
                        )
                        _interruptible_sleep(config["micro_pause_duration"], wait_gate)
                        if self.stop_reason == "runtime_limit":
                            break

                    actual_delay = config["delay"]
                    if config["delay_variance"] > 0:
                        actual_delay = max(0.0, config["delay"] + random.uniform(-config["delay_variance"], config["delay_variance"]))

                    if actual_delay > 0:
                        _interruptible_sleep(actual_delay, wait_gate)
                        if self.stop_reason == "runtime_limit":
                            break
                    else:
                        # Zero delay in dry-run emits no throttling call at all; without this
                        # yield the loop pegs a core and starves the stop-hotkey poll.
                        time.sleep(0)
                        if config["dry_run"] and total_actions % 256 == 0:
                            time.sleep(0.001)
            except Exception as exc:
                self.stop_reason = "error"
                self.ui_queue.put(("status", f"Run stopped by an internal error: {exc}"))
            finally:
                # Always restore the globals; leaking FAILSAFE=False used to disarm the
                # corner escape for every later tool window in the process.
                try:
                    pyautogui.FAILSAFE = previous_failsafe
                    pyautogui.PAUSE = previous_pause
                except Exception:
                    pass
                finish(time.perf_counter() - started_at)

        def _finish_run(self, total_actions, elapsed, last_click_point, generation=None):
            # A "finished" message from an earlier run must never tear down a newer one:
            # the ~100 ms pump gap used to leave a live run with no handle and a dead Stop button.
            if generation is not None and generation != self.active_run_generation:
                return
            self.worker_thread = None
            self.pause_event.clear()
            self._refresh_run_buttons()
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
            self.lifetime_stats["runs"] = self.lifetime_stats.get("runs", 0) + 1
            self.lifetime_stats["actions"] = self.lifetime_stats.get("actions", 0) + int(total_actions)
            self.lifetime_stats["seconds"] = round(self.lifetime_stats.get("seconds", 0.0) + float(elapsed), 3)
            self._write_run_log(self.run_reports[-1])
            self.stop_reason = "idle"
            self.active_run_was_dry_run = False
            self._schedule_workspace_save()

        def _busy_subsystem(self):
            """Name whichever input-injecting subsystem is live, else None."""
            if self.worker_thread and self.worker_thread.is_alive():
                return "click run"
            if self.sequence_thread and self.sequence_thread.is_alive():
                return "coordinate sequence"
            if self.is_playing:
                return "recording playback"
            return None

        def _refresh_run_buttons(self):
            """Keep Start/Stop/Pause in step with whatever is actually running."""
            busy = self._busy_subsystem()
            if hasattr(self, "start_button"):
                self.start_button.configure(state=DISABLED if busy else NORMAL)
            if hasattr(self, "stop_button"):
                self.stop_button.configure(state=NORMAL if busy else DISABLED)
            if hasattr(self, "pause_button"):
                self.pause_button.configure(state=NORMAL if busy else DISABLED)
                self.pause_button.configure(text="Resume" if self.pause_event.is_set() else "Pause")

        def startclick(self):
            busy = self._busy_subsystem()
            if busy:
                self.status_var.set(f"A {busy} is already active. Stop it before starting a click run.")
                return

            try:
                config = self._build_run_config()
            except ValueError as exc:
                messagebox.showerror("Invalid configuration", str(exc), parent=self)
                return

            self.stop_event.clear()
            self.pause_event.clear()
            self.stop_reason = "running"
            self.hotkey_notified = False
            self.rate_samples = []
            self.active_run_was_dry_run = bool(config["dry_run"])
            self.run_generation += 1
            self.active_run_generation = self.run_generation
            config["generation"] = self.run_generation
            config["targets"] = self._active_target_list(config)
            self.session_var.set("Starting dry run..." if config["dry_run"] else "Starting click run...")
            schedule = config.get("schedule") or {}
            if schedule.get("scheduled"):
                self.status_var.set(f"Scheduled start armed. {schedule.get('detail', '')}")
            elif config["countdown"] > 0:
                self.status_var.set(f"Countdown armed for {config['countdown']:.2f}s. Use Stop or the configured hotkey to cancel.")
            else:
                self.status_var.set("Dry run started. No clicks will be sent." if config["dry_run"] else "Run started. Use Stop or the configured hotkey to end it.")
            target_note = f"{len(config['targets'])} target(s)" if len(config["targets"]) > 1 else f"{config['x']}, {config['y']}"
            self._append_activity(
                f"{'Dry run' if config['dry_run'] else 'Run'} started at {target_note} using {config['click_mode']}."
            )

            self.worker_thread = threading.Thread(target=self._click_worker, args=(config,), daemon=True)
            self.worker_thread.start()
            self._refresh_run_buttons()

            if self.minimize_on_start_var.get():
                self.was_minimized_for_run = True
                self.iconify()

            self._schedule_workspace_save()

        def _active_target_list(self, config):
            """Screen points this run cycles through: the recording when round-robin is on."""
            if self.round_robin_var.get() and self.recording_data:
                points = []
                for point in self.recording_data:
                    try:
                        points.append((int(point[0]), int(point[1])))
                    except Exception:
                        continue
                if points:
                    return points
            return [(config["x"], config["y"])]

        def toggle_pause(self):
            if not self._busy_subsystem():
                self.status_var.set("Nothing is running to pause.")
                return
            if self.pause_event.is_set():
                self.pause_event.clear()
                self.status_var.set("Resuming.")
                self._append_activity("Run resumed.")
            else:
                self.pause_event.set()
                self.status_var.set("Pause requested. The run holds after the current action.")
                self._append_activity("Run paused.")
            self._refresh_run_buttons()

        def stopclick(self):
            stopped_any = False
            self.pause_event.clear()
            if self.worker_thread and self.worker_thread.is_alive():
                self.stop_reason = "manual"
                self.stop_event.set()
                self.status_var.set("Stop requested. Waiting for the current loop to finish.")
                self._append_activity("Stop requested for the active run.")
                stopped_any = True
            if self.sequence_thread and self.sequence_thread.is_alive():
                self.sequence_stop_event.set()
                self.status_var.set("Stopping coordinate sequence after the current step.")
                self._append_activity("Stop requested for coordinate sequence.")
                stopped_any = True
            if self.is_playing:
                self.playback_stop_event.set()
                self.status_var.set("Stopping playback after the current point.")
                self._append_activity("Stop requested for playback.")
                stopped_any = True
            if not stopped_any:
                self.status_var.set("Nothing is running.")
            self._refresh_run_buttons()

        def _write_run_log(self, report):
            """Append one JSON line per finished run to an always-on, size-capped log."""
            try:
                log_path = _state_file_location(RUN_LOG_FILE_NAME)
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                if os.path.exists(log_path) and os.path.getsize(log_path) > 1_000_000:
                    _rotate_run_log(log_path)
                with open(log_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(report, sort_keys=True, default=str) + "\n")
            except Exception:
                pass

        def _capture_theme_roles(self, widget=None):
            """Record the palette role of every widget from its authored colour."""
            widget = self if widget is None else widget
            for option, sentinels in (("bg", self.BG_ROLE_SENTINELS), ("fg", self.FG_ROLE_SENTINELS)):
                key = (str(widget), option)
                if key in self._theme_roles:
                    continue
                try:
                    self._theme_roles[key] = sentinels.get(widget.cget(option))
                except Exception:
                    self._theme_roles[key] = None
            for child in widget.winfo_children():
                self._capture_theme_roles(child)

        def _apply_theme(self):
            palette = self._theme_palette()
            self._refresh_ttk_styles(palette)
            # Capture first: widgets built since the last pass are still in their authored
            # colours, and reading them after configure() would record the wrong role.
            self._capture_theme_roles()
            self.configure(bg=palette["main_bg"])

            # Roles are resolved once, from the widget's build-time colour, and cached by
            # widget path. Re-deriving the role from the *current* colour on every switch
            # was self-corrupting: Light hero_bg and Dark main_bg are both #0f172a, so
            # Dark -> Light left page frames dark and eventually put white text on a light page.
            roles = self._theme_roles

            def role_for(widget, option, sentinel_map):
                key = (str(widget), option)
                if key not in roles:
                    try:
                        roles[key] = sentinel_map.get(widget.cget(option))
                    except Exception:
                        roles[key] = None
                return roles[key]

            def walk(widget):
                try:
                    bg_role = role_for(widget, "bg", self.BG_ROLE_SENTINELS)
                    if bg_role:
                        widget.configure(bg=palette[bg_role])

                    fg_role = role_for(widget, "fg", self.FG_ROLE_SENTINELS)
                    if fg_role:
                        widget.configure(fg=palette[fg_role])

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
            """Capture a point. Runs on the `keyboard` hook thread, not the Tk thread."""
            if not self.is_recording:
                return
            try:
                x_pos, y_pos = pyautogui.position()
            except Exception:
                return
            # The Tk thread rebinds self.recording_data wholesale (load, clear, shift), so
            # appending from this thread could write into a list that is no longer the
            # live one. Marshalling the mutation to the Tk thread removes the race.
            try:
                self.after(0, self._append_recorded_point, int(x_pos), int(y_pos))
            except Exception:
                return
            if winsound:
                try:
                    winsound.Beep(800, 50)
                except Exception:
                    pass

        def _append_recorded_point(self, x_pos, y_pos):
            if not self.is_recording:
                return
            self.recording_data.append((x_pos, y_pos))
            self.status_var.set(f"Captured ({x_pos}, {y_pos}). Total: {len(self.recording_data)}")

        def _play_recording(self):
            if not self.recording_data:
                messagebox.showinfo("Playback", "No recording found. Record some points first.")
                return
            busy = self._busy_subsystem()
            if busy:
                self.status_var.set(f"Stop the active {busy} before starting playback.")
                return

            # Snapshot everything off the Tk thread; the worker must not read Tk vars.
            try:
                playback_config = self._build_run_config()
            except ValueError as exc:
                messagebox.showerror("Invalid configuration", str(exc), parent=self)
                return
            playback_config["points"] = [(int(p[0]), int(p[1])) for p in list(self.recording_data)]

            self.playback_stop_event.clear()
            self.pause_event.clear()
            self.hotkey_notified = False
            self.is_playing = True
            self._refresh_run_buttons()
            threading.Thread(target=self._playback_worker, args=(playback_config,), daemon=True).start()
            self._append_activity(
                f"{'Playback simulation' if playback_config['dry_run'] else 'Playback'} started for "
                f"{len(playback_config['points'])} recorded point(s)."
            )

        def _playback_worker(self, config):
            """Play recorded points using the same action, fail-safe and stop rules as a run."""
            dry_run = bool(config["dry_run"])
            points = config["points"]
            stop_event = self.playback_stop_event
            previous_failsafe = getattr(pyautogui, "FAILSAFE", True)
            previous_pause = getattr(pyautogui, "PAUSE", 0.1)
            completed = 0

            def should_stop():
                return self._stop_requested(config["stop_hotkey"], stop_event)

            self._set_status_safe(f"{'Simulating playback for' if dry_run else 'Playing back'} {len(points)} points...")
            try:
                try:
                    pyautogui.FAILSAFE = bool(config["pyautogui_failsafe"])
                    if config.get("pacing_mode", "Precise") == "Precise":
                        pyautogui.PAUSE = 0
                except Exception:
                    pass

                delay = max(0.0, float(config.get("delay", 0.5)))
                for index, (x_pos, y_pos) in enumerate(points):
                    if should_stop():
                        break
                    if not self._wait_while_paused(config, stop_event):
                        break
                    point = (
                        max(0, min(self.screen_width - 1, int(x_pos))),
                        max(0, min(self.screen_height - 1, int(y_pos))),
                    )
                    self._emit_action(config, point, stop_event)
                    if not dry_run:
                        self.session_clicks += 1
                    completed = index + 1
                    self._set_status_safe(f"{'Playback simulation' if dry_run else 'Playback'}: {completed}/{len(points)}")
                    if config["max_actions"] > 0 and completed >= config["max_actions"]:
                        self._set_status_safe(f"Playback stopped at the {config['max_actions']} action cap.")
                        break
                    if not _interruptible_sleep(delay, should_stop):
                        break
            except Exception as exc:
                if exc.__class__.__name__ == "FailSafeException":
                    self._set_status_safe("Corner fail-safe triggered. Playback stopped.")
                else:
                    self._set_status_safe(f"Playback error: {exc}")
            finally:
                # is_playing must be cleared on every path, or Start / Play / Run Sequence
                # all stay locked out for the rest of the session.
                try:
                    pyautogui.FAILSAFE = previous_failsafe
                    pyautogui.PAUSE = previous_pause
                except Exception:
                    pass
                self.is_playing = False
                stopped = stop_event.is_set()
                if stopped:
                    self._set_status_safe("Playback stopped.")
                    self._append_activity(f"Playback stopped after {completed} of {len(points)} point(s).")
                else:
                    self._set_status_safe("Playback simulation finished." if dry_run else "Playback finished.")
                    self._append_activity(
                        f"{'Playback simulation' if dry_run else 'Playback'} finished after {completed} point(s)."
                    )
                if self.play_sound_var.get() and winsound:
                    try:
                        winsound.Beep(1200, 200)
                    except Exception:
                        pass
                stop_event.clear()
                self.ui_queue.put(("refresh_buttons", None))
                self._schedule_workspace_save()

        def _update_dashboard(self):
            try:
                self.total_session_clicks_var.set(f"Total Session Clicks: {self.session_clicks}")
                self.recording_summary_var.set(
                    f"Recording: {len(self.recording_data)} point(s) | {'active' if self.is_recording else 'idle'}"
                )

                elapsed = int(time.time() - self.session_start_time)
                hours, remainder = divmod(elapsed, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.session_elapsed_var.set(f"Session Elapsed: {hours:02}:{minutes:02}:{seconds:02}")

                lifetime = self.lifetime_stats
                self.lifetime_stats_var.set(
                    f"Lifetime: {lifetime.get('runs', 0)} run(s) | {lifetime.get('actions', 0)} action(s) | "
                    f"{_format_seconds(lifetime.get('seconds', 0.0))}"
                )
            except Exception:
                pass
            finally:
                # Rescheduling from `finally` means one bad frame can no longer freeze
                # the dashboard for the rest of the session.
                try:
                    self.after(1000, self._update_dashboard)
                except Exception:
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
                    _atomic_write_json(file_path, self.recording_data)
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
                return _normalize_sequence_steps(raw_steps, self.ACTION_TYPES)

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
                if action_name not in self.ACTION_TYPES:
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

            def run_sequence_worker(sequence_copy, loop_count, countdown_seconds, dry_run, run_settings):
                completed_steps = 0
                previous_failsafe = getattr(pyautogui, "FAILSAFE", True)
                previous_pause = getattr(pyautogui, "PAUSE", 0.1)
                stop_event = self.sequence_stop_event
                stop_hotkey = run_settings.get("stop_hotkey", "")

                def should_stop():
                    return self._stop_requested(stop_hotkey, stop_event)

                try:
                    pyautogui.FAILSAFE = bool(run_settings.get("pyautogui_failsafe"))
                    if run_settings.get("pacing_mode", "Precise") == "Precise":
                        pyautogui.PAUSE = 0
                    if countdown_seconds > 0:
                        target_time = time.perf_counter() + countdown_seconds
                        last_announced = None
                        while True:
                            remaining = target_time - time.perf_counter()
                            if remaining <= 0:
                                break
                            if should_stop():
                                self.ui_queue.put(("status", "Coordinate sequence cancelled during countdown."))
                                self._append_activity("Sequence cancelled during countdown.")
                                return
                            announced_value = int(math.ceil(remaining))
                            if announced_value != last_announced:
                                self.ui_queue.put(("status", f"Sequence starting in {announced_value}s."))
                                last_announced = announced_value
                            _interruptible_sleep(min(0.1, remaining), should_stop, slice_seconds=0.05)

                    for loop_index in range(loop_count):
                        for x_pos, y_pos, action_name, delay_seconds in sequence_copy:
                            if should_stop():
                                self.ui_queue.put(("status", f"Coordinate sequence stopped after {completed_steps} step(s)."))
                                self._append_activity(f"Sequence stopped after {completed_steps} step(s).")
                                return
                            if not self._wait_while_paused(run_settings, stop_event):
                                self.ui_queue.put(("status", f"Coordinate sequence stopped after {completed_steps} step(s)."))
                                return
                            step_config = dict(run_settings, click_mode=action_name, dry_run=dry_run)
                            try:
                                self._emit_action(step_config, (x_pos, y_pos), stop_event)
                            except Exception as exc:
                                if exc.__class__.__name__ == "FailSafeException":
                                    self.ui_queue.put(("status", f"Corner fail-safe stopped the sequence after {completed_steps} step(s)."))
                                    self._append_activity(f"Corner fail-safe stopped the sequence after {completed_steps} step(s).")
                                else:
                                    self.ui_queue.put(("status", f"Sequence step error: {exc}"))
                                    self._append_activity(f"Sequence step error: {exc}")
                                return
                            completed_steps += 1
                            if delay_seconds > 0 and not _interruptible_sleep(delay_seconds, should_stop):
                                self.ui_queue.put(("status", f"Coordinate sequence stopped after {completed_steps} step(s)."))
                                self._append_activity(f"Sequence stopped after {completed_steps} step(s).")
                                return
                        self.ui_queue.put(("status", f"Sequence loop {loop_index + 1}/{loop_count} complete."))
                    self.ui_queue.put(("status", f"{'Dry-run sequence' if dry_run else 'Coordinate sequence'} complete. Ran {completed_steps} step(s)."))
                    self._append_activity(f"{'Dry-run sequence' if dry_run else 'Sequence'} complete. Ran {completed_steps} step(s).")
                except Exception as exc:
                    self.ui_queue.put(("status", f"Sequence error: {exc}"))
                    self._append_activity(f"Sequence error: {exc}")
                finally:
                    try:
                        pyautogui.FAILSAFE = previous_failsafe
                        pyautogui.PAUSE = previous_pause
                    except Exception:
                        pass
                    self.sequence_thread = None
                    stop_event.clear()
                    self.ui_queue.put(("refresh_buttons", None))

            def launch_sequence(start_from_selected=False):
                if not steps:
                    messagebox.showinfo("Sequence builder", "Add at least one step before running the sequence.", parent=window)
                    return
                busy = self._busy_subsystem()
                if busy:
                    messagebox.showinfo("Sequence builder", f"Stop the active {busy} before starting a sequence.", parent=window)
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

                self.sequence_stop_event.clear()
                self.pause_event.clear()
                self.hotkey_notified = False
                dry_run = bool(self.dry_run_var.get())
                # Snapshot Tk state here so the worker thread never reads a Tk variable.
                run_settings = {
                    "stop_hotkey": self.stop_hotkey_var.get().strip(),
                    "pyautogui_failsafe": bool(self.pyautogui_failsafe_var.get()),
                    "pacing_mode": self.pacing_mode_var.get(),
                    "dry_run": dry_run,
                    "action_key": self.action_key_var.get().strip(),
                    "action_text": self.action_text_var.get(),
                    "scroll_amount": int(self.scroll_amount_var.get() or 3),
                    "hold_duration": float(self.hold_duration_var.get() or 0.25),
                    "drag_to_x": int(self.drag_to_x_var.get() or 0),
                    "drag_to_y": int(self.drag_to_y_var.get() or 0),
                }
                self.status_var.set(
                    f"{'Simulating' if dry_run else 'Running'} coordinate sequence {start_label} with {len(sequence_copy)} step(s)."
                )
                self._append_activity(
                    f"{'Dry-run sequence' if dry_run else 'Sequence'} started {start_label} with {len(sequence_copy)} step(s) across {loop_count} loop(s)."
                )
                self.sequence_thread = threading.Thread(
                    target=run_sequence_worker,
                    args=(sequence_copy, loop_count, countdown_seconds, dry_run, run_settings),
                    daemon=True,
                )
                self.sequence_thread.start()
                self._refresh_run_buttons()

            def save_sequence():
                if not steps:
                    messagebox.showinfo("Sequence builder", "Add at least one step before saving.", parent=window)
                    return
                file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], parent=window)
                if not file_path:
                    return
                try:
                    _atomic_write_json(file_path, steps)
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
            ttk.Combobox(editor_card, textvariable=action_var, values=tuple(self.ACTION_TYPES.keys()), state="readonly", width=18).grid(row=2, column=2, sticky="w", padx=(12, 0), pady=(4, 0))
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
            palette = self._theme_palette()
            mini = tk.Toplevel(self)
            mini.overrideredirect(True)
            mini.attributes("-topmost", True)
            mini.attributes("-alpha", 0.92)
            mini.geometry("232x74+100+100")
            mini.configure(bg=palette["hero_chip_bg"])

            # Drag logic. The grip label is the handle, so the buttons stay clickable.
            def start_move(event):
                mini.x, mini.y = event.x, event.y

            def do_move(event):
                x_pos = mini.winfo_x() + (event.x - mini.x)
                y_pos = mini.winfo_y() + (event.y - mini.y)
                mini.geometry(f"+{x_pos}+{y_pos}")

            frame = tk.Frame(mini, bg=palette["hero_chip_bg"], padx=6, pady=5)
            frame.pack(fill="both", expand=True)

            grip = tk.Label(frame, text="::", bg=palette["hero_chip_bg"], fg=palette["hero_sub"],
                            font=("Segoe UI", 11, "bold"), cursor="fleur")
            grip.pack(side="left", padx=(2, 6))
            for widget in (mini, frame, grip):
                widget.bind("<Button-1>", start_move)
                widget.bind("<B1-Motion>", do_move)

            btn_start = tk.Button(frame, text="Start", bg=palette["accent"], fg="white",
                                  font=("Segoe UI", 9, "bold"), bd=0, command=self.startclick, width=5)
            btn_start.pack(side="left", padx=2)
            btn_pause = tk.Button(frame, text="Pause", bg=palette["secondary_bg"], fg=palette["secondary_fg"],
                                  font=("Segoe UI", 9, "bold"), bd=0, command=self.toggle_pause, width=6)
            btn_pause.pack(side="left", padx=2)
            btn_stop = tk.Button(frame, text="Stop", bg=palette["danger"], fg="white",
                                 font=("Segoe UI", 9, "bold"), bd=0, command=self.stopclick, width=5)
            btn_stop.pack(side="left", padx=2)
            tk.Button(frame, text="X", bg=palette["hero_chip_bg"], fg=palette["hero_sub"],
                      font=("Segoe UI", 9, "bold"), bd=0, command=mini.destroy, width=2).pack(side="right")

            state_var = tk.StringVar(value="Idle")
            tk.Label(mini, textvariable=state_var, bg=palette["hero_chip_bg"], fg=palette["hero_sub"],
                     font=("Segoe UI", 8)).place(x=8, y=54)

            def refresh_state():
                """Mini Control used to give no indication of what the app was doing."""
                if not mini.winfo_exists():
                    return
                busy = self._busy_subsystem()
                if busy and self.pause_event.is_set():
                    state_var.set(f"Paused - {busy}")
                elif busy:
                    state_var.set(f"Running - {busy}")
                else:
                    state_var.set("Idle")
                btn_start.configure(state=DISABLED if busy else NORMAL)
                btn_pause.configure(state=NORMAL if busy else DISABLED,
                                    text="Resume" if self.pause_event.is_set() else "Pause")
                btn_stop.configure(state=NORMAL if busy else DISABLED)
                mini.after(250, refresh_state)

            refresh_state()



        def _setup_tray(self):
            try:
                from PIL import Image
                image = Image.open(_resource_path("favicon.ico"))
                menu = (
                    item('Restore', self._restore_from_tray),
                    # Tray callbacks arrive on the pystray thread; hop to the Tk thread.
                    item('Start Clicker', lambda: self.after(0, self.startclick)),
                    item('Pause / Resume', lambda: self.after(0, self.toggle_pause)),
                    item('Stop Clicker', lambda: self.after(0, self.stopclick)),
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
            self.pause_event.clear()
            for event in (self.stop_event, self.sequence_stop_event, self.playback_stop_event):
                event.set()
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
            self._unregister_global_hotkeys()
            if self.tray_icon is not None:
                try:
                    self.tray_icon.stop()
                except:
                    pass
                self.tray_icon = None
            self._persist_workspace_state()
            self.destroy()

    your_gui = YourGUI()
    your_gui.mainloop()
    time.sleep(0)

# --------------------------------------------------------------------------------------
# Headless command line
# --------------------------------------------------------------------------------------

CLI_EXIT_OK = 0
CLI_EXIT_FAILED = 1
CLI_EXIT_USAGE = 2

# Legacy V10.1 flags stay supported so existing scripts keep working.
LEGACY_FLAG_COMMANDS = {
    "--health-check": ["health"],
    "--health": ["health"],
    "--health-json": ["health", "--json"],
    "--state-summary": ["state-summary"],
    "--state-json": ["state-summary", "--json"],
    "--backup-state": ["backup-state"],
    "--validate-recording": ["validate-recording"],
    "--validate-sequence": ["validate-sequence"],
    "--validate-profiles": ["validate-profiles"],
    "--profile-import-preview": ["profile-preview"],
}


def _cli_envelope(command, ok, data=None, errors=None):
    """Uniform JSON shape for every command, including usage errors."""
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "command": command,
        "ok": bool(ok),
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "data": data if data is not None else {},
        "errors": list(errors or []),
    }


def _translate_legacy_args(argv):
    """Map old single-flag invocations onto the subcommand grammar.

    Returns (translated_args, ignored_flags). Unknown input passes through so argparse can
    report it, instead of silently falling through and opening the GUI on a CI runner.
    """
    argv = list(argv or [])
    if not argv:
        return argv, []

    legacy_flags = [arg for arg in argv if arg.split("=", 1)[0] in LEGACY_FLAG_COMMANDS]
    if not legacy_flags:
        return argv, []

    # First flag wins, matching V10.1 dispatch order, but any extras are now reported
    # rather than silently discarded behind a success exit code.
    primary = legacy_flags[0]
    flag_name, _, inline_value = primary.partition("=")
    translated = list(LEGACY_FLAG_COMMANDS[flag_name])

    value = inline_value or _argument_value(argv, flag_name)
    if value:
        translated.append(value)
    if "--json" in argv and "--json" not in translated:
        translated.append("--json")
    return translated, list(legacy_flags[1:])


def _build_cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="AutoClicker",
        description="AutoClicker Control Center. Run with no arguments to open the GUI.",
        epilog="Exit codes: 0 success, 1 check or validation failure, 2 usage error, 3 internal error.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"AutoClicker {APP_VERSION} (Python {sys.version.split()[0]}, {platform.system()})",
    )
    subparsers = parser.add_subparsers(dest="command")

    def add(name, help_text):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--json", action="store_true", help="emit a machine-readable JSON envelope")
        return sub

    add("gui", "open the Control Center window")

    health = add("health", "report dependency, version and state-file health")
    health.add_argument("--strict", action="store_true", help="exit 1 when a required dependency is missing")

    add("state-summary", "summarise the saved profile and workspace files")

    backup = add("backup-state", "copy the app-state files into a timestamped folder")
    backup.add_argument("destination", nargs="?", help="target directory (defaults to the state folder)")
    backup.add_argument("--dry-run", action="store_true", help="show what would be copied without writing")

    bundle = add("support-bundle", "write a full support bundle for troubleshooting")
    bundle.add_argument("destination", nargs="?", help="target directory")

    for name, help_text in (
        ("validate-recording", "validate one or more recording JSON files"),
        ("validate-sequence", "validate one or more sequence JSON files"),
        ("validate-profiles", "validate one or more profiles JSON files"),
    ):
        sub = add(name, help_text)
        sub.add_argument("paths", nargs="+", help="one or more JSON files")

    preview = add("profile-preview", "preview importing a profiles file over the saved profiles")
    preview.add_argument("paths", nargs="+", help="one or more JSON files")
    preview.add_argument("--show-values", action="store_true", help="include full profile payloads in JSON output")

    profiles = add("profiles", "list saved profiles, or show one by name")
    profiles.add_argument("name", nargs="?", help="show a single profile instead of listing all")

    readiness = add("readiness", "run the pre-flight readiness checklist for a saved profile")
    readiness.add_argument("name", help="profile name")

    schema = add("schema", "print the accepted shape of a file or action type")
    schema.add_argument("kind", choices=("recording", "sequence", "profile", "action"))

    history = add("history", "summarise the persistent run log")
    history.add_argument("--limit", type=int, default=20, help="how many recent runs to show")

    add("doctor", "report health plus the exact pip command that fixes it")

    return parser


def _cli_load_saved_profiles():
    path = _state_file_location(PROFILE_FILE_NAME)
    if not os.path.exists(path):
        return {}, path
    loaded = _load_json_file(path)
    return (loaded if isinstance(loaded, dict) else {}), path


def _cli_emit(args, command, ok, data, errors, text_lines):
    """Print either the JSON envelope or the human report, and return the exit code."""
    errors = list(errors or [])
    if getattr(args, "json", False):
        print(json.dumps(_cli_envelope(command, ok, data, errors), indent=2, sort_keys=True, default=str))
    else:
        for line in text_lines:
            print(line)
        for error in errors:
            print(error, file=sys.stderr)
    return CLI_EXIT_OK if ok else CLI_EXIT_FAILED


def _cli_validate_files(args, command, validator, describe, extra_errors=None):
    """Validate every supplied path; the command fails if any single file fails."""
    results, errors, lines = [], list(extra_errors or []), []
    file_type = command.replace("validate-", "")
    for path in args.paths:
        try:
            result = validator(path)
        except Exception as exc:
            result = {"valid": False, "path": path, "error": str(exc)}
        result.setdefault("path", path)
        result["type"] = file_type
        results.append(result)
        if result.get("valid"):
            lines.append(f"OK   {path}: {describe(result)}")
        else:
            errors.append(f"FAIL {path}: {result.get('error', 'did not pass validation')}")
    ok = bool(results) and all(r.get("valid") for r in results)
    return _cli_emit(args, command, ok, {"results": results, "count": len(results)}, errors, lines)


def _readiness_config_from_profile(profile):
    """Project a saved profile onto the run-config shape the readiness checker expects."""
    profile = profile or {}

    def number(name, default=0.0):
        try:
            return float(profile.get(name, default))
        except Exception:
            return default

    repeat_limit = None
    if str(profile.get("repeat_mode", "Infinite")) == "Burst Count":
        try:
            repeat_limit = int(profile.get("repeat_count", 0))
        except Exception:
            repeat_limit = None

    return {
        "x": int(number("target_x")),
        "y": int(number("target_y")),
        "delay": number("delay"),
        "runtime_limit": number("runtime_limit"),
        "max_actions": int(number("max_actions")),
        "repeat_limit": repeat_limit,
        "stop_hotkey": str(profile.get("stop_hotkey", "")),
        "dry_run": bool(profile.get("dry_run")),
        "pyautogui_failsafe": bool(profile.get("pyautogui_failsafe")),
        "human_like": bool(profile.get("human_like")),
        "pacing_mode": str(profile.get("pacing_mode", "Precise")),
        "click_mode": str(profile.get("click_mode", "Left Click")),
        "action_key": profile.get("action_key", ACTION_DEFAULTS["action_key"]),
        "action_text": profile.get("action_text", ACTION_DEFAULTS["action_text"]),
        "scroll_amount": profile.get("scroll_amount", ACTION_DEFAULTS["scroll_amount"]),
        "hold_duration": profile.get("hold_duration", ACTION_DEFAULTS["hold_duration"]),
        "drag_to_x": profile.get("drag_to_x", ACTION_DEFAULTS["drag_to_x"]),
        "drag_to_y": profile.get("drag_to_y", ACTION_DEFAULTS["drag_to_y"]),
        "schedule": _parse_scheduled_start(profile.get("scheduled_start")),
    }


def _describe_schema(kind):
    """Machine-readable description of each accepted file or action shape."""
    if kind == "recording":
        return {
            "kind": "recording",
            "description": "JSON array of [x, y] screen points.",
            "max_points": 200,
            "example": [[100, 200], [340, 512]],
        }
    if kind == "sequence":
        return {
            "kind": "sequence",
            "description": "JSON array of [x, y, action_name, delay_seconds] steps.",
            "action_names": sorted(ACTION_REGISTRY),
            "example": [[100, 200, "Left Click", 0.5], [340, 512, "Scroll Down", 0.25]],
        }
    if kind == "profile":
        return {
            "kind": "profile",
            "description": "JSON object mapping profile name to a settings object.",
            "fields": sorted(PROFILE_FIELDS),
            "int_fields": sorted(PROFILE_INT_FIELDS),
            "float_fields": sorted(PROFILE_FLOAT_FIELDS),
            "bool_fields": sorted(PROFILE_BOOL_FIELDS),
            "enum_fields": {name: sorted(values) for name, values in PROFILE_ENUM_FIELDS.items()},
        }
    return {
        "kind": "action",
        "description": "Actions the run engine can emit.",
        "actions": {
            name: {
                "kind": spec["kind"],
                "uses": list(spec.get("uses", ())),
                "button": spec.get("button"),
                "clicks": spec.get("clicks"),
            }
            for name, spec in ACTION_REGISTRY.items()
        },
        "defaults": dict(ACTION_DEFAULTS),
    }


def _run_cli(argv):
    """Dispatch a headless command. Returns an exit code, or None to open the GUI."""
    translated, ignored_flags = _translate_legacy_args(argv)
    parser = _build_cli_parser()
    args = parser.parse_args(translated)
    command = args.command

    if command is None or command == "gui":
        return None

    conflict_errors = []
    if ignored_flags:
        # V10.1 dropped later subcommands silently and still exited 0, so a CI job could
        # turn green without running the check it asked for.
        conflict_errors.append(
            f"Ignored extra legacy flag(s): {', '.join(ignored_flags)}. Run one command at a time."
        )

    if command in ("health", "doctor"):
        data = _collect_headless_health_data()
        missing = data.get("missing_required") or []
        missing_optional = sorted(
            name for name, item in data["dependencies"].items()
            if not item["available"] and not item.get("required")
        )
        strict = bool(getattr(args, "strict", False))
        data["fix_command"] = f"pip install {' '.join(missing)}" if missing else ""
        data["missing_optional"] = missing_optional
        lines = _build_headless_health_report().split("\n")
        if command == "doctor":
            lines += ["", "Doctor"]
            if missing:
                lines.append(f"- Required, install now: pip install {' '.join(missing)}")
            if missing_optional:
                lines.append(f"- Optional, unlocks more features: pip install {' '.join(missing_optional)}")
            if not missing and not missing_optional:
                lines.append("- Everything this app can use is installed.")
        # `health` stays exit 0 by default for backwards compatibility; --strict and
        # `doctor` are the gate-able forms.
        fail_on_missing = strict or command == "doctor"
        errors = conflict_errors + ([f"Missing required dependency: {name}" for name in missing] if fail_on_missing else [])
        ok = not (fail_on_missing and missing)
        return _cli_emit(args, command, ok, data, errors, lines)

    if command == "state-summary":
        data = _collect_state_summary_data()
        errors = list(conflict_errors)
        for key in ("profiles", "workspace"):
            entry = data.get(key)
            if isinstance(entry, dict) and entry.get("error"):
                errors.append(f"{key}: {entry['error']}")
        ok = not any(e for e in errors if not e.startswith("Ignored"))
        return _cli_emit(args, command, ok, data, errors, _build_state_summary_report().split("\n"))

    if command == "backup-state":
        if args.dry_run:
            summary = _collect_state_summary_data()
            planned = [entry["path"] for entry in summary.values()
                       if isinstance(entry, dict) and entry.get("present")]
            lines = ["Dry run: nothing written.", f"Would copy {len(planned)} file(s):"]
            lines += [f"- {path}" for path in planned]
            return _cli_emit(args, command, True, {"dry_run": True, "planned_files": planned}, conflict_errors, lines)
        result = _backup_state_files(args.destination)
        lines = [f"State backup directory: {result['backup_dir']}", f"Copied files: {result['count']}"]
        lines += [f"- {name}" for name in result["copied_files"]]
        return _cli_emit(args, command, True, result, conflict_errors, lines)

    if command == "support-bundle":
        result = _build_support_bundle(args.destination)
        lines = [f"Support bundle: {result.get('bundle_dir', '?')}", f"Files: {len(result.get('files', []))}"]
        lines += [f"- {name}" for name in result.get("files", [])]
        return _cli_emit(args, command, True, result, conflict_errors, lines)

    if command == "validate-recording":
        return _cli_validate_files(args, command, _validate_recording_file,
                                   lambda r: f"{r['points']} point(s)", conflict_errors)
    if command == "validate-sequence":
        return _cli_validate_files(args, command, _validate_sequence_file,
                                   lambda r: f"{r['steps']} step(s), {r['total_wait_seconds']:.3f}s total wait",
                                   conflict_errors)
    if command == "validate-profiles":
        return _cli_validate_files(args, command, _validate_profiles_file,
                                   lambda r: f"{r['valid_count']} valid, {r['invalid_count']} invalid",
                                   conflict_errors)

    if command == "profile-preview":
        existing, _path = _cli_load_saved_profiles()
        results, errors, lines = [], list(conflict_errors), []
        for path in args.paths:
            try:
                result = _validate_profiles_file(path, existing_profiles=existing)
            except Exception as exc:
                result = {"valid": False, "path": path, "error": str(exc)}
            result.setdefault("path", path)
            if not args.show_values:
                # Payloads carry hotkeys and window layouts; dumping them is opt-in.
                result.pop("profiles", None)
            results.append(result)
            if result.get("valid"):
                lines.append(
                    f"OK   {path}: {result['valid_count']} valid, {result['invalid_count']} invalid, "
                    f"{result['overwrite_count']} overwrite(s)"
                )
            else:
                errors.append(f"FAIL {path}: {result.get('error', 'did not pass validation')}")
        ok = bool(results) and all(r.get("valid") for r in results)
        return _cli_emit(args, command, ok, {"results": results}, errors, lines)

    if command == "profiles":
        profiles, path = _cli_load_saved_profiles()
        if args.name:
            profile = profiles.get(args.name)
            if profile is None:
                return _cli_emit(args, command, False, {"path": path, "name": args.name},
                                 conflict_errors + [f"No saved profile named '{args.name}'."], [])
            lines = [f"Profile: {args.name}"] + [f"- {key}: {value}" for key, value in sorted(profile.items())]
            return _cli_emit(args, command, True,
                             {"path": path, "name": args.name, "profile": profile}, conflict_errors, lines)
        names = sorted(profiles)
        lines = [f"Profiles file: {path}", f"Saved profiles: {len(names)}"] + [f"- {name}" for name in names]
        return _cli_emit(args, command, True,
                         {"path": path, "names": names, "count": len(names)}, conflict_errors, lines)

    if command == "readiness":
        profiles, path = _cli_load_saved_profiles()
        profile = profiles.get(args.name)
        if profile is None:
            return _cli_emit(args, command, False, {"path": path, "name": args.name},
                             conflict_errors + [f"No saved profile named '{args.name}'."], [])
        validation = _validate_profile_data(args.name, profile)
        readiness = _build_readiness_checklist(_readiness_config_from_profile(profile))
        ok = bool(readiness["ready"] and validation["valid"])
        errors = conflict_errors + ([] if validation["valid"] else list(validation["errors"]))
        return _cli_emit(args, command, ok,
                         {"name": args.name, "readiness": readiness, "validation": validation},
                         errors, _format_readiness_text(readiness, limit=20).split("\n"))

    if command == "schema":
        data = _describe_schema(args.kind)
        lines = [f"{args.kind} schema", ""] + json.dumps(data, indent=2, sort_keys=True).split("\n")
        return _cli_emit(args, command, True, data, conflict_errors, lines)

    if command == "history":
        log_path = _state_file_location(RUN_LOG_FILE_NAME)
        records = _read_run_log(log_path, limit=max(1, args.limit))
        summary = _summarize_run_history(records)
        lines = [
            f"Run log: {log_path}",
            f"{summary['runs']} run(s) ({summary['live_runs']} live, {summary['dry_runs']} dry), "
            f"{summary['actions']} action(s), {_format_seconds(summary['seconds'])}, "
            f"{summary['average_cps']:.2f} action(s)/sec average",
            "",
        ]
        for record in reversed(records):
            lines.append(
                f"{record.get('finished_at', '?')}  {'DRY ' if record.get('dry_run') else 'LIVE'}  "
                f"{record.get('click_mode', '?')}  {record.get('actions', 0)} action(s)  "
                f"{record.get('stop_reason', '?')}"
            )
        if not records:
            lines.append("No runs recorded yet.")
        return _cli_emit(args, command, True,
                         {"log_path": log_path, "summary": summary, "runs": records}, conflict_errors, lines)

    parser.error(f"Unknown command: {command}")


if __name__ == '__main__':
    try:
        _exit_code = _run_cli(sys.argv[1:])
    except SystemExit:
        raise
    except Exception as _exc:
        print(f"AutoClicker failed: {_exc}", file=sys.stderr)
        raise SystemExit(3)

    if _exit_code is None:
        MAINWINDOW_REDESIGNED()
    else:
        raise SystemExit(_exit_code)
