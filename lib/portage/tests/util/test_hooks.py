# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

import os
import tempfile
from pathlib import Path

import portage
from portage.tests import TestCase
from portage.util.hooks import get_hooks_from_dir, perform_hooks


class HookDirectoryTestCase(TestCase):
    def _write_hook(self, configroot, name, source, executable=True):
        directory = Path(configroot) / portage.USER_CONFIG_PATH / "postemerge.d"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text("#!/bin/sh\n" + source, encoding="utf-8")
        path.chmod(0o700 if executable else 0o600)
        return path

    def test_argv_preserves_spaces_and_metacharacters(self):
        with tempfile.TemporaryDirectory(prefix="portage-hooks-") as root:
            output = Path(root) / "output file"
            marker = Path(root) / "injected"
            self._write_hook(root, "10-test", 'printf "%s\\n" "$@" > "$1"\n')
            argument = f"$(touch {marker})"
            perform_hooks(
                "postemerge.d",
                str(output),
                "two words",
                argument,
                prefix=root,
            )
            self.assertEqual(
                output.read_text(encoding="utf-8").splitlines(),
                [str(output), "two words", argument],
            )
            self.assertFalse(marker.exists())

    def test_lexical_order_failure_and_nonexecutable(self):
        with tempfile.TemporaryDirectory(prefix="portage-hooks-") as root:
            output = Path(root) / "output"
            self._write_hook(root, "20-second", 'echo second >> "$1"\n')
            self._write_hook(root, "10-first", 'echo first >> "$1"\nexit 7\n')
            self._write_hook(root, "30-disabled", 'echo disabled >> "$1"\n', executable=False)
            self.assertEqual(
                [Path(name).name for name in get_hooks_from_dir("postemerge.d", prefix=root)],
                ["10-first", "20-second"],
            )
            perform_hooks("postemerge.d", str(output), prefix=root)
            self.assertEqual(
                output.read_text(encoding="utf-8").splitlines(),
                ["first", "second"],
            )

    def test_only_selected_config_root_is_scanned(self):
        with tempfile.TemporaryDirectory(prefix="portage-hooks-") as root:
            configroot = Path(root) / "selected"
            output = Path(root) / "output"
            self._write_hook(
                configroot,
                "10-selected",
                'echo selected >> "$1"\n',
            )
            perform_hooks("postemerge.d", str(output), prefix=str(configroot))
            self.assertEqual(output.read_text(encoding="utf-8").strip(), "selected")
