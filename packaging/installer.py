import argparse
import os
import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

APP_NAME = "AutoClicker"


def _app_version(default="V11.0"):
    """Prefer the version recorded in the source tree; fall back when frozen."""
    source_file = Path(__file__).resolve().parents[1] / "AutoClicker.py"
    try:
        for line in source_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("APP_VERSION"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return default


VERSION = _app_version()
PAYLOAD_FILES = (
    "AutoClicker.exe",
    "AutoClickerLite.exe",
    "favicon.ico",
    "README.md",
    "LICENSE",
    "requirements.txt",
)


def payload_root():
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    if (base_dir / "payload").exists():
        return base_dir / "payload"
    return base_dir


def default_install_dir():
    local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return local_appdata / "Programs" / APP_NAME / VERSION


def start_menu_dir():
    appdata = Path(os.environ.get("APPDATA", Path.home()))
    return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME


def desktop_dir():
    return Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"


def create_hidden_root():
    root = tk.Tk()
    root.withdraw()
    return root


def info(message, silent=False, parent=None):
    if silent:
        print(message)
        return
    messagebox.showinfo(APP_NAME, message, parent=parent)


def error(message, silent=False, parent=None):
    if silent:
        print(message, file=sys.stderr)
        return
    messagebox.showerror(APP_NAME, message, parent=parent)


def ask_install_dir(parent):
    if messagebox.askyesno(
        APP_NAME,
        f"Install {APP_NAME} {VERSION} to the default location?\n\n{default_install_dir()}",
        parent=parent,
    ):
        return default_install_dir()

    selected = filedialog.askdirectory(
        title=f"Choose an install directory for {APP_NAME}",
        mustexist=False,
        parent=parent,
    )
    if not selected:
        return None

    return Path(selected) / APP_NAME / VERSION


def create_shortcut(shortcut_path, target_path, icon_path, working_dir):
    import win32com.client

    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.TargetPath = str(target_path)
    shortcut.WorkingDirectory = str(working_dir)
    shortcut.IconLocation = str(icon_path)
    shortcut.Save()


def assert_safe_install_dir(install_dir):
    """Refuse to recursively delete anything that is not an AutoClicker install.

    `--install-dir` feeds straight into shutil.rmtree, so pointing it at C:\\ or at a
    home directory would wipe it. A target must be non-existent, empty, or a directory
    this installer previously wrote.
    """
    install_dir = Path(install_dir).resolve()

    forbidden = {Path(p).resolve() for p in filter(None, (
        os.environ.get("SystemDrive", "C:") + os.sep,
        os.environ.get("SystemRoot"),
        os.environ.get("ProgramFiles"),
        os.environ.get("USERPROFILE"),
        os.environ.get("APPDATA"),
        os.environ.get("LOCALAPPDATA"),
        str(Path.home()),
    ))}
    if install_dir in forbidden or install_dir.parent == install_dir:
        raise ValueError(f"Refusing to install into a protected location: {install_dir}")

    if not install_dir.exists():
        return install_dir
    if not install_dir.is_dir():
        raise ValueError(f"Install target is not a directory: {install_dir}")

    existing = set(os.listdir(install_dir))
    if not existing:
        return install_dir
    if existing <= set(PAYLOAD_FILES) or (install_dir / "AutoClicker.exe").exists():
        return install_dir
    raise ValueError(
        f"Refusing to erase {install_dir}: it is not empty and does not look like an "
        f"existing {APP_NAME} install."
    )


def install_payload(install_dir, make_shortcuts):
    source_root = payload_root()
    missing_files = [name for name in PAYLOAD_FILES if not (source_root / name).exists()]
    if missing_files:
        raise FileNotFoundError(
            "Installer payload is incomplete. Missing: " + ", ".join(missing_files)
        )

    install_dir = assert_safe_install_dir(install_dir)
    if install_dir.exists():
        shutil.rmtree(install_dir)
    install_dir.mkdir(parents=True, exist_ok=True)

    for file_name in PAYLOAD_FILES:
        shutil.copy2(source_root / file_name, install_dir / file_name)

    if make_shortcuts:
        icon_path = install_dir / "favicon.ico"
        create_shortcut(
            desktop_dir() / f"{APP_NAME}.lnk",
            install_dir / "AutoClicker.exe",
            icon_path,
            install_dir,
        )
        create_shortcut(
            desktop_dir() / f"{APP_NAME} Lite.lnk",
            install_dir / "AutoClickerLite.exe",
            icon_path,
            install_dir,
        )
        create_shortcut(
            start_menu_dir() / f"{APP_NAME}.lnk",
            install_dir / "AutoClicker.exe",
            icon_path,
            install_dir,
        )
        create_shortcut(
            start_menu_dir() / f"{APP_NAME} Lite.lnk",
            install_dir / "AutoClickerLite.exe",
            icon_path,
            install_dir,
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Install AutoClicker.")
    parser.add_argument("--silent", action="store_true", help="Install without message boxes.")
    parser.add_argument("--install-dir", type=Path, help="Override the install directory.")
    parser.add_argument("--no-shortcuts", action="store_true", help="Do not create desktop or Start Menu shortcuts.")
    parser.add_argument("--launch", action="store_true", help="Launch the main app after install.")
    return parser.parse_args()


def main():
    args = parse_args()
    root = None
    try:
        if not args.silent:
            root = create_hidden_root()

        install_dir = args.install_dir
        if install_dir is None:
            if args.silent:
                install_dir = default_install_dir()
            else:
                install_dir = ask_install_dir(root)
                if install_dir is None:
                    return 1

        install_dir = Path(install_dir)
        install_payload(install_dir, make_shortcuts=not args.no_shortcuts)

        if args.launch:
            os.startfile(str(install_dir / "AutoClicker.exe"))

        info(
            f"{APP_NAME} {VERSION} was installed to:\n{install_dir}",
            silent=args.silent,
            parent=root,
        )
        return 0
    except Exception as exc:
        error(f"Installer failed.\n\n{exc}", silent=args.silent, parent=root)
        return 1
    finally:
        if root is not None:
            root.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
