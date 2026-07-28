"""Safe tests for the macOS desktop shortcut installer."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "install-desktop-shortcut"
ZSH = Path("/bin/zsh")


@unittest.skipUnless(ZSH.exists(), "/bin/zsh is required")
class TestDesktopShortcutInstaller(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.repository = base / "repo with spaces & quote's"
        self.repository.mkdir()
        self.desktop = base / "Desktop Test"
        shutil.copy2(INSTALLER, self.repository / INSTALLER.name)
        (self.repository / INSTALLER.name).chmod(0o700)
        (self.repository / "portfolio.py").write_text("# test fixture\n", encoding="utf-8")
        self.sync_log = base / "sync.log"
        self._write_mock_sync(0)
        subprocess.run(["git", "init", "-q", str(self.repository)], check=True)

    def tearDown(self):
        self.temporary.cleanup()

    @property
    def launcher(self) -> Path:
        return self.desktop / "Sync Cybersecurity Portfolio.command"

    def _write_mock_sync(self, status: int) -> None:
        sync = self.repository / "sync-portfolio"
        sync.write_text(
            "#!/bin/zsh\n"
            "set -u\n"
            f"print -r -- \"$PWD\" > {self._zsh_quote(self.sync_log)}\n"
            f"exit {status}\n",
            encoding="utf-8",
        )
        sync.chmod(0o700)

    @staticmethod
    def _zsh_quote(path: Path) -> str:
        return "'" + str(path).replace("'", "'\\''") + "'"

    def _install(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(self.repository / INSTALLER.name),
             "--desktop-dir", str(self.desktop), *extra],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_install_is_idempotent_and_launcher_reaches_mock(self):
        first = self._install()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(self.launcher.exists())
        self.assertTrue(os.access(self.launcher, os.X_OK))
        initial = self.launcher.read_bytes()

        syntax = subprocess.run(
            [str(ZSH), "-n", str(self.launcher)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        content = initial.decode()
        self.assertIn("typeset -r REPOSITORY_ROOT=", content)
        self.assertIn("./sync-portfolio", content)

        second = self._install()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.launcher.read_bytes(), initial)

        launched = subprocess.run(
            [str(self.launcher)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            launched.returncode, 0,
            f"stdout:\n{launched.stdout}\nstderr:\n{launched.stderr}",
        )
        self.assertIn("completed successfully", launched.stdout)
        self.assertEqual(self.sync_log.read_text(encoding="utf-8").strip(),
                         str(self.repository.resolve()))

    def test_launcher_preserves_mock_failure_status(self):
        installed = self._install()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self._write_mock_sync(7)

        launched = subprocess.run(
            [str(self.launcher)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            launched.returncode, 7,
            f"stdout:\n{launched.stdout}\nstderr:\n{launched.stderr}",
        )
        self.assertIn("failed with exit status 7", launched.stderr)

    def test_launcher_reports_missing_repository(self):
        installed = self._install()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        moved_repository = self.repository.with_name("repository moved")
        self.repository.rename(moved_repository)

        launched = subprocess.run(
            [str(self.launcher)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(launched.returncode, 1)
        self.assertIn("Repository directory no longer exists", launched.stderr)

    def test_dry_run_does_not_create_desktop_or_launcher(self):
        result = self._install("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Validated desktop shortcut", result.stdout)
        self.assertFalse(self.desktop.exists())
        self.assertFalse(self.launcher.exists())

    def test_missing_sync_command_is_rejected(self):
        (self.repository / "sync-portfolio").unlink()
        result = self._install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sync-portfolio is missing", result.stderr)
        self.assertFalse(self.launcher.exists())

    def test_non_executable_sync_command_is_rejected(self):
        (self.repository / "sync-portfolio").chmod(0o600)
        result = self._install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sync-portfolio is not executable", result.stderr)
        self.assertFalse(self.launcher.exists())

    def test_non_file_launcher_target_is_rejected(self):
        self.launcher.mkdir(parents=True)
        result = self._install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-file launcher target", result.stderr)
        self.assertTrue(self.launcher.is_dir())


if __name__ == "__main__":
    unittest.main()
