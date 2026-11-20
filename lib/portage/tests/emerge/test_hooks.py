# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

import os
from unittest.mock import MagicMock, patch

from _emerge.EbuildMerge import EbuildMerge
from _emerge.Scheduler import Scheduler
from _emerge.actions import _run_ask_hooks
from portage.tests import TestCase


class EmergeHookTestCase(TestCase):
    def test_ask_hook_reads_manifest_and_cleanup(self):
        captured = {}

        def read_manifest(name, path, *, prefix):
            self.assertEqual(name, "ask.d")
            self.assertEqual(prefix, "/configured")
            captured["path"] = path
            with open(path, encoding="utf-8") as handle:
                captured["body"] = handle.read()

        with patch("_emerge.actions.perform_hooks", side_effect=read_manifest):
            _run_ask_hooks(
                [("app-misc/first-1", "merge"), ("app-misc/second-2", "uninstall")],
                "/configured",
            )
        self.assertEqual(
            captured["body"], "app-misc/first-1 merge\napp-misc/second-2 uninstall\n"
        )
        self.assertFalse(os.path.exists(captured["path"]))

    def test_ask_hook_cleans_up_on_exception(self):
        captured = {}

        def reject(name, path, *, prefix):
            captured["path"] = path
            raise RuntimeError("hook failed")

        with patch("_emerge.actions.perform_hooks", side_effect=reject):
            with self.assertRaisesRegex(RuntimeError, "hook failed"):
                _run_ask_hooks([("app-misc/first-1", "merge")], "/configured")
        self.assertFalse(os.path.exists(captured["path"]))

    def test_merge_success_and_postinst_failure_are_distinct(self):
        for failed in (False, True):
            with self.subTest(postinst_failure=failed):
                merge = MagicMock()
                merge._final_exit.return_value = 0
                merge.pkg.cpv = "app-misc/test-1"
                merge.pkg.root = "/target"
                merge.settings.features = set()
                merge.settings.__getitem__.return_value = "/configured"
                with patch("_emerge.EbuildMerge.perform_hooks") as hooks:
                    EbuildMerge._merge_exit(merge, MagicMock(postinst_failure=failed))
                if failed:
                    hooks.assert_not_called()
                else:
                    hooks.assert_called_once_with(
                        "ebuild.postmerge.d",
                        "app-misc/test-1",
                        "/target",
                        prefix="/configured",
                    )
                merge._start_exit_hook.assert_called_once()

    def test_failed_package_dispatches_to_selected_config_root(self):
        scheduler = MagicMock()
        scheduler._failed_pkgs = []
        scheduler._terminated_tasks = False
        package = MagicMock(cpv="app-misc/test-1", root="/target")
        settings = {
            "PORTAGE_CONFIGROOT": "/configured",
            "PORTAGE_BUILDDIR": "/tmp/build",
            "PORTAGE_LOG_FILE": "/tmp/build/log",
        }
        with patch("_emerge.Scheduler.perform_hooks") as hooks:
            Scheduler._record_pkg_failure(scheduler, package, settings, 1)
        hooks.assert_called_once_with(
            "ebuild.postfail.d",
            "app-misc/test-1",
            "/target",
            prefix="/configured",
        )
        self.assertEqual(len(scheduler._failed_pkgs), 1)
