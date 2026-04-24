import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import sys

IMPORT_ERRORS = {}

try:
    import keyboard
except Exception as exc:
    keyboard = None
    IMPORT_ERRORS["keyboard"] = str(exc)

try:
    import pyautogui
except Exception as exc:
    pyautogui = None
    IMPORT_ERRORS["pyautogui"] = str(exc)


def _missing_packages(packages):
    return [package for package in packages if package in IMPORT_ERRORS]


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
    missing = _missing_packages(packages)
    if missing:
        _show_dependency_error(feature_name, missing, parent=parent)
        return False
    return True


class AutoClickerGUI(tk.Tk):
    CLICK_MAP = {
        "Left Click": ("left", 1),
        "Right Click": ("right", 1),
        "Middle Click": ("middle", 1),
        "Double Left Click": ("left", 2),
    }

    def __init__(self):
        super().__init__()
        self.title("AutoClicker Lite")
        self.geometry("360x500+400+260")
        self.attributes("-topmost", True)
        self.configure(bg="#0f172a")
        self.resizable(False, False)

        try:
            self.iconbitmap("favicon.ico")
        except:
            pass

        self.input_x_var = tk.StringVar(value="")
        self.input_y_var = tk.StringVar(value="")
        self.click_mode_var = tk.StringVar(value="Left Click")
        self.delay_var = tk.StringVar(value="0.10")
        self.stop_hotkey_var = tk.StringVar(value="q")
        self.repeat_mode_var = tk.StringVar(value="Infinite")
        self.burst_count_var = tk.StringVar(value="25")
        self.status_var = tk.StringVar(value="Ready. Capture a point and press Start.")
        self.session_var = tk.StringVar(value="Session clicks: 0")

        self.is_running = False
        self.stop_event = threading.Event()
        self.session_clicks = 0

        self._build_ui()

        self.repeat_mode_var.trace_add("write", self._update_repeat_state)
        self._update_repeat_state()
        self._apply_dependency_state()

    def _build_ui(self):
        tk.Label(
            self,
            text="AutoClicker Lite",
            bg="#0f172a",
            fg="#f8fafc",
            font=("Segoe UI", 17, "bold"),
        ).pack(pady=(18, 4))
        tk.Label(
            self,
            text="Compact mode with safer stop controls and burst runs.",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        ).pack(pady=(0, 18))

        card = tk.Frame(self, bg="#f8fafc", padx=16, pady=16)
        card.pack(fill="x", padx=16)
        card.columnconfigure(1, weight=1)

        tk.Label(card, text="Target X", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(card, textvariable=self.input_x_var, width=14).grid(row=0, column=1, sticky="ew", pady=(0, 6))
        tk.Label(card, text="Target Y", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(card, textvariable=self.input_y_var, width=14).grid(row=1, column=1, sticky="ew", pady=(0, 6))
        self.capture_button = ttk.Button(card, text="Use Current Cursor", command=self._capture_cursor)
        self.capture_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        tk.Label(card, text="Click type", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 6))
        ttk.Combobox(
            card,
            textvariable=self.click_mode_var,
            values=tuple(self.CLICK_MAP.keys()),
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", pady=(0, 6))

        tk.Label(card, text="Delay (sec)", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(card, textvariable=self.delay_var).grid(row=4, column=1, sticky="ew", pady=(0, 6))

        tk.Label(card, text="Stop hotkey", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(card, textvariable=self.stop_hotkey_var).grid(row=5, column=1, sticky="ew", pady=(0, 6))

        tk.Label(card, text="Repeat mode", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky="w", pady=(0, 6))
        ttk.Combobox(
            card,
            textvariable=self.repeat_mode_var,
            values=("Infinite", "Burst Count"),
            state="readonly",
        ).grid(row=6, column=1, sticky="ew", pady=(0, 6))

        tk.Label(card, text="Burst count", bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 9, "bold")).grid(row=7, column=0, sticky="w", pady=(0, 6))
        self.burst_entry = ttk.Entry(card, textvariable=self.burst_count_var)
        self.burst_entry.grid(row=7, column=1, sticky="ew", pady=(0, 6))

        tk.Label(
            card,
            textvariable=self.session_var,
            bg="#f8fafc",
            fg="#0f766e",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 0))

        button_row = tk.Frame(self, bg="#0f172a")
        button_row.pack(fill="x", padx=16, pady=18)
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)

        self.start_button = tk.Button(
            button_row,
            text="START",
            bg="#0f766e",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            bd=0,
            command=self.start_clicking,
        )
        self.start_button.grid(row=0, column=0, sticky="ew")

        self.stop_button = tk.Button(
            button_row,
            text="STOP",
            bg="#b91c1c",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            bd=0,
            state="disabled",
            command=self.stop_clicking,
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        status_card = tk.Frame(self, bg="#111827", padx=14, pady=14)
        status_card.pack(fill="x", padx=16)
        tk.Label(status_card, text="Status", bg="#111827", fg="#f8fafc", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(
            status_card,
            textvariable=self.status_var,
            bg="#111827",
            fg="#cbd5e1",
            font=("Segoe UI", 9),
            wraplength=300,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

    def _apply_dependency_state(self):
        missing = _missing_packages(["pyautogui", "keyboard"])
        if not missing:
            return

        self.start_button.configure(state="disabled", bg="#94a3b8")
        self.capture_button.configure(state="disabled")
        self.status_var.set(
            "Install pyautogui and keyboard to enable Lite mode."
        )

    def _update_repeat_state(self, *_args):
        if self.repeat_mode_var.get() == "Infinite":
            self.burst_entry.configure(state="disabled")
        else:
            self.burst_entry.configure(state="normal")

    def _capture_cursor(self):
        if not _ensure_dependencies("AutoClicker Lite", ["pyautogui"], parent=self):
            return

        try:
            x_pos, y_pos = pyautogui.position()
        except Exception as exc:
            messagebox.showerror("Capture failed", f"Unable to read the cursor position.\n{exc}", parent=self)
            return

        self.input_x_var.set(str(x_pos))
        self.input_y_var.set(str(y_pos))
        self.status_var.set(f"Captured cursor position {x_pos}, {y_pos}.")

    def _set_running_state(self, running):
        self.is_running = running
        self.start_button.configure(
            text="RUNNING..." if running else "START",
            bg="#94a3b8" if running else "#0f766e",
            state="disabled" if running else "normal",
        )
        self.stop_button.configure(state="normal" if running else "disabled")

    def start_clicking(self):
        if self.is_running:
            return
        if not _ensure_dependencies("AutoClicker Lite", ["pyautogui", "keyboard"], parent=self):
            return

        try:
            x_pos = int(self.input_x_var.get())
            y_pos = int(self.input_y_var.get())
            delay = float(self.delay_var.get())
            if delay < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input", "Enter valid numeric X, Y, and delay values.", parent=self)
            return

        click_mode = self.click_mode_var.get()
        if click_mode not in self.CLICK_MAP:
            messagebox.showerror("Invalid click type", "Choose a valid click type.", parent=self)
            return

        stop_hotkey = self.stop_hotkey_var.get().strip().lower()
        if self.repeat_mode_var.get() == "Infinite" and not stop_hotkey:
            messagebox.showerror("Stop hotkey required", "Set a stop hotkey before starting an infinite run.", parent=self)
            return

        repeat_limit = None
        if self.repeat_mode_var.get() == "Burst Count":
            try:
                repeat_limit = int(self.burst_count_var.get())
                if repeat_limit < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid burst count", "Burst count must be a whole number greater than zero.", parent=self)
                return

        self.stop_event.clear()
        self.session_clicks = 0
        self.session_var.set("Session clicks: 0")
        self._set_running_state(True)
        self.status_var.set("Click run started. Use Stop or the configured hotkey to end it.")

        threading.Thread(
            target=self._click_worker,
            args=(x_pos, y_pos, delay, click_mode, stop_hotkey, repeat_limit),
            daemon=True,
        ).start()

    def stop_clicking(self):
        if self.is_running:
            self.stop_event.set()
            self.status_var.set("Stop requested. Waiting for the current loop to finish.")

    def _click_worker(self, x_pos, y_pos, delay, click_mode, stop_hotkey, repeat_limit):
        button_name, click_count = self.CLICK_MAP[click_mode]
        reason = "completed"

        try:
            pyautogui.FAILSAFE = True

            while not self.stop_event.is_set():
                if stop_hotkey:
                    try:
                        if keyboard.is_pressed(stop_hotkey):
                            reason = "hotkey"
                            self.stop_event.set()
                            break
                    except:
                        pass

                pyautogui.click(
                    x=x_pos,
                    y=y_pos,
                    button=button_name,
                    clicks=click_count,
                    interval=0.02 if click_count > 1 else 0.0,
                )
                self.session_clicks += 1
                self.after(0, lambda count=self.session_clicks: self.session_var.set(f"Session clicks: {count}"))

                if repeat_limit is not None and self.session_clicks >= repeat_limit:
                    reason = "burst"
                    break

                if delay > 0:
                    wake_at = time.perf_counter() + delay
                    while time.perf_counter() < wake_at:
                        if self.stop_event.is_set():
                            reason = "manual"
                            break
                        if stop_hotkey:
                            try:
                                if keyboard.is_pressed(stop_hotkey):
                                    reason = "hotkey"
                                    self.stop_event.set()
                                    break
                            except:
                                pass
                        time.sleep(min(0.02, wake_at - time.perf_counter()))
            if self.stop_event.is_set() and reason == "completed":
                reason = "manual"
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Clicker error", str(exc), parent=self))
            reason = "error"
        finally:
            self.after(0, lambda: self._finish_run(reason, stop_hotkey))

    def _finish_run(self, reason, stop_hotkey):
        self._set_running_state(False)
        self.stop_event.clear()

        if reason == "burst":
            self.status_var.set(f"Burst complete after {self.session_clicks} click action(s).")
        elif reason == "hotkey":
            self.status_var.set(f"Stopped by hotkey '{stop_hotkey}' after {self.session_clicks} click action(s).")
        elif reason == "manual":
            self.status_var.set(f"Stopped manually after {self.session_clicks} click action(s).")
        elif reason == "error":
            self.status_var.set("Run stopped because of an error.")
        else:
            self.status_var.set(f"Run finished after {self.session_clicks} click action(s).")


if __name__ == "__main__":
    app = AutoClickerGUI()
    app.mainloop()
