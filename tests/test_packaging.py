"""Guards on packaging metadata and repository hygiene."""

import os
import re
import subprocess
import unittest

import AutoClicker

REPO_ROOT = os.path.dirname(os.path.abspath(AutoClicker.__file__))


def read(*parts):
    with open(os.path.join(REPO_ROOT, *parts), "r", encoding="utf-8") as handle:
        return handle.read()


class VersionConsistencyTests(unittest.TestCase):
    def test_build_script_derives_the_version_from_the_app(self):
        # The version used to be hard-coded in three files and drifted between them.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "build_release", os.path.join(REPO_ROOT, "packaging", "build_release.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.VERSION, AutoClicker.APP_VERSION)

    def test_installer_derives_the_version_from_the_app(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "acinstaller", os.path.join(REPO_ROOT, "packaging", "installer.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.VERSION, AutoClicker.APP_VERSION)

    def test_readme_mentions_the_current_version(self):
        self.assertIn(AutoClicker.APP_VERSION, read("README.md"))


class SecretHygieneTests(unittest.TestCase):
    def test_no_credential_files_are_tracked(self):
        result = subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            self.skipTest("not a git checkout")
        offenders = [
            path for path in result.stdout.splitlines()
            if re.search(r"(^|/)creds\.json$|\.pem$|\.key$", path)
        ]
        self.assertEqual(offenders, [], f"Credential files are tracked: {offenders}")

    def test_gitignore_blocks_credential_files(self):
        gitignore = read(".gitignore")
        self.assertIn("creds.json", gitignore)

    def test_no_private_key_material_in_source_files(self):
        for name in ("AutoClicker.py", "lite-version.py", "requirements.txt", "README.md"):
            with self.subTest(file=name):
                self.assertNotIn("PRIVATE KEY", read(name))


class RequirementsTests(unittest.TestCase):
    def test_retired_dependencies_are_gone(self):
        requirements = read("requirements.txt")
        source = read("AutoClicker.py")
        for retired in ("gspread", "oauth2client", "colormap", "pywin32"):
            with self.subTest(package=retired):
                # Comments explain the removal, so only check real requirement lines.
                lines = [
                    line.split("#")[0].strip()
                    for line in requirements.splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
                self.assertFalse(
                    any(line.startswith(retired) for line in lines),
                    f"{retired} is still required but never imported",
                )
                self.assertNotIn(f"import {retired}", source)

    def test_every_catalogued_dependency_is_declared(self):
        requirements = read("requirements.txt").lower()
        for name in AutoClicker.DEPENDENCY_CATALOGUE:
            with self.subTest(package=name):
                self.assertIn(name.lower(), requirements)

    def test_required_dependencies_are_marked_required(self):
        catalogue = AutoClicker.DEPENDENCY_CATALOGUE
        self.assertTrue(catalogue["pyautogui"]["required"])
        self.assertTrue(catalogue["keyboard"]["required"])
        self.assertFalse(catalogue["pystray"]["required"])

    def test_opencv_is_declared_because_photo_clicker_passes_confidence(self):
        # pyautogui raises unless OpenCV is installed when confidence= is used.
        self.assertIn("confidence=", read("AutoClicker.py"))
        self.assertIn("opencv-python", read("requirements.txt"))


class DeadCodeTests(unittest.TestCase):
    def test_no_duplicate_top_level_definitions(self):
        import ast
        import collections

        tree = ast.parse(read("AutoClicker.py"))
        counts = collections.Counter(
            node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        )
        duplicates = {name: count for name, count in counts.items() if count > 1}
        self.assertEqual(duplicates, {}, f"Shadowed top-level definitions: {duplicates}")

    def test_no_duplicate_methods_within_a_class(self):
        import ast
        import collections

        tree = ast.parse(read("AutoClicker.py"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            counts = collections.Counter(
                child.name for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.ClassDef))
            )
            duplicates = {name: count for name, count in counts.items() if count > 1}
            self.assertEqual(duplicates, {}, f"{node.name} has shadowed methods: {duplicates}")

    def test_retired_dead_functions_are_gone(self):
        source = read("AutoClicker.py")
        self.assertNotIn("def MAINWINDOW_NEWSTYLE", source)
        self.assertNotIn("class Coordinates(", source)

    def test_no_function_hides_its_body_behind_a_main_guard(self):
        # `if __name__ == '__main__'` nested inside OldStyleGUI() made the menu item a
        # silent no-op whenever the module was imported instead of run directly.
        import ast

        def is_main_guard(test):
            return (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
                and any(isinstance(c, ast.Constant) and c.value == "__main__" for c in test.comparators)
            )

        tree = ast.parse(read("AutoClicker.py"))
        offenders = [
            f"{node.name}:{child.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            for child in ast.walk(node)
            if isinstance(child, ast.If) and is_main_guard(child.test)
        ]
        self.assertEqual(offenders, [], f"Nested __main__ guards found: {offenders}")


if __name__ == "__main__":
    unittest.main()
