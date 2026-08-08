from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _app_version() -> str:
    """Read APP_VERSION straight from the source so the three files cannot drift."""
    source = (ROOT / "AutoClicker.py").read_text(encoding="utf-8")
    for line in source.splitlines():
        if line.startswith("APP_VERSION"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("APP_VERSION not found in AutoClicker.py")


VERSION = _app_version()
BUILD_ROOT = ROOT / "Builds" / VERSION
EXECUTABLE_DIR = BUILD_ROOT / "Executable"
INSTALLER_DIR = BUILD_ROOT / "Installer"
PYINSTALLER_ROOT = ROOT / "build" / "pyinstaller"
DATA_SEPARATOR = ";" if os.name == "nt" else ":"

MAIN_SCRIPT = ROOT / "AutoClicker.py"
LITE_SCRIPT = ROOT / "lite-version.py"
INSTALLER_SCRIPT = ROOT / "packaging" / "installer.py"
ICON_PATH = ROOT / "favicon.ico"

ROOT_PAYLOAD_FILES = (
    ROOT / "favicon.ico",
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / "requirements.txt",
)


def run_pyinstaller(*args: str) -> None:
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", *args]
    print("Running:", " ".join(f'"{part}"' if " " in part else part for part in command))
    subprocess.run(command, cwd=ROOT, check=True)


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_payload_files() -> None:
    for file_path in ROOT_PAYLOAD_FILES:
        shutil.copy2(file_path, EXECUTABLE_DIR / file_path.name)


def add_data_argument(source: Path, destination: str) -> str:
    return f"{source}{DATA_SEPARATOR}{destination}"


def build_main_executable() -> None:
    run_pyinstaller(
        "--name",
        "AutoClicker",
        "--onefile",
        "--windowed",
        "--icon",
        str(ICON_PATH),
        "--distpath",
        str(EXECUTABLE_DIR),
        "--workpath",
        str(PYINSTALLER_ROOT / "autoclicker" / "build"),
        "--specpath",
        str(PYINSTALLER_ROOT / "autoclicker" / "spec"),
        # The window icon is loaded at runtime via _resource_path("favicon.ico"); without
        # --add-data the onefile bundle has no such file and iconbitmap() fails silently.
        "--add-data",
        add_data_argument(ICON_PATH, "."),
        "--collect-submodules",
        "pystray",
        "--collect-submodules",
        "win10toast",
        str(MAIN_SCRIPT),
    )


def build_lite_executable() -> None:
    run_pyinstaller(
        "--name",
        "AutoClickerLite",
        "--onefile",
        "--windowed",
        "--icon",
        str(ICON_PATH),
        "--distpath",
        str(EXECUTABLE_DIR),
        "--workpath",
        str(PYINSTALLER_ROOT / "lite" / "build"),
        "--specpath",
        str(PYINSTALLER_ROOT / "lite" / "spec"),
        "--add-data",
        add_data_argument(ICON_PATH, "."),
        str(LITE_SCRIPT),
    )


def build_installer() -> None:
    run_pyinstaller(
        "--name",
        "AutoClickerInstaller",
        "--onefile",
        "--windowed",
        "--icon",
        str(ICON_PATH),
        "--distpath",
        str(INSTALLER_DIR),
        "--workpath",
        str(PYINSTALLER_ROOT / "installer" / "build"),
        "--specpath",
        str(PYINSTALLER_ROOT / "installer" / "spec"),
        "--hidden-import",
        "win32com.client",
        "--add-data",
        add_data_argument(EXECUTABLE_DIR / "AutoClicker.exe", "payload"),
        "--add-data",
        add_data_argument(EXECUTABLE_DIR / "AutoClickerLite.exe", "payload"),
        "--add-data",
        add_data_argument(ROOT / "favicon.ico", "payload"),
        "--add-data",
        add_data_argument(ROOT / "README.md", "payload"),
        "--add-data",
        add_data_argument(ROOT / "LICENSE", "payload"),
        "--add-data",
        add_data_argument(ROOT / "requirements.txt", "payload"),
        str(INSTALLER_SCRIPT),
    )


def preflight() -> None:
    """Fail before anything is deleted.

    ensure_clean_dir() rmtree's the tracked Builds/<version> folders, so a missing
    PyInstaller used to destroy the previous release and only then error out.
    """
    import importlib.util

    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit(
            "PyInstaller is not installed. Run: pip install -r requirements-build.txt"
        )
    for required in (MAIN_SCRIPT, LITE_SCRIPT, INSTALLER_SCRIPT, ICON_PATH, *ROOT_PAYLOAD_FILES):
        if not Path(required).exists():
            raise SystemExit(f"Missing build input: {required}")


def verify_outputs() -> None:
    """Confirm the build actually produced what it claims."""
    expected = [
        EXECUTABLE_DIR / "AutoClicker.exe",
        EXECUTABLE_DIR / "AutoClickerLite.exe",
        INSTALLER_DIR / "AutoClickerInstaller.exe",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    if missing:
        raise SystemExit("Build finished but these artifacts are missing:\n  " + "\n  ".join(missing))
    for path in expected:
        print(f"  {path.name}: {path.stat().st_size / 1_048_576:.1f} MB")


def main() -> int:
    print(f"Building AutoClicker {VERSION} (version read from AutoClicker.py)")
    preflight()

    ensure_clean_dir(EXECUTABLE_DIR)
    ensure_clean_dir(INSTALLER_DIR)
    ensure_clean_dir(PYINSTALLER_ROOT)

    build_main_executable()
    build_lite_executable()
    copy_payload_files()
    build_installer()
    verify_outputs()

    print(f"Release artifacts written to: {BUILD_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
