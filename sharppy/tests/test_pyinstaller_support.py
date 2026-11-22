"""Build-resource checks that do not import Qt or run PyInstaller."""

import importlib
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from runsharp.pyinstaller_support import (
    collect_windows_resources,
    collect_windows_ssl_binaries,
    write_version_runtime_hook,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class WindowsPackagingTests(unittest.TestCase):
    def test_resources_do_not_depend_on_working_directory(self):
        previous = Path.cwd()
        with TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                resources = collect_windows_resources(PROJECT_ROOT)
            finally:
                os.chdir(previous)
        source_paths = {Path(source) for source, _ in resources}
        self.assertIn(PROJECT_ROOT / 'datasources' / 'standard.xml', source_paths)
        self.assertIn(PROJECT_ROOT / 'datasources' / 'spc_ua.csv', source_paths)
        self.assertIn(PROJECT_ROOT / 'rc' / 'sample_std.png', source_paths)
        for source, destination in resources:
            self.assertTrue(Path(source).is_absolute())
            self.assertTrue(Path(source).is_file())
            if Path(source).parent == PROJECT_ROOT / 'datasources':
                self.assertEqual(destination, 'sharppy/datasources')
        self.assertFalse(any('__pycache__' in source for source, _ in resources))

    def test_missing_resources_fail_before_building(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(FileNotFoundError, 'Missing SHARPpy resource'):
                collect_windows_resources(temp)

    def test_ssl_dlls_are_collected_from_interpreter_prefixes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / 'environment'
            base = root / 'base'
            for prefix in (first, base):
                (prefix / 'DLLs').mkdir(parents=True)
                for name in ('libcrypto-1_1-x64.dll', 'libssl-1_1-x64.dll'):
                    (prefix / 'DLLs' / name).write_bytes(b'fixture')
            binaries = collect_windows_ssl_binaries([first, base])
            self.assertEqual(len(binaries), 2)
            self.assertTrue(all(Path(source).parent == first / 'DLLs'
                                for source, _ in binaries))
            self.assertTrue(all(destination == '.' for _, destination in binaries))

    def test_missing_ssl_family_reports_the_required_dll(self):
        with TemporaryDirectory() as temp:
            (Path(temp) / 'libcrypto-1_1-x64.dll').write_bytes(b'fixture')
            with self.assertRaisesRegex(RuntimeError, 'libssl'):
                collect_windows_ssl_binaries([temp])

    def test_frozen_version_hook_preserves_metadata_without_source_edits(self):
        version_file = PROJECT_ROOT / 'sharppy' / '_version.py'
        original = version_file.read_bytes()
        version = {'version': '1.4.0+test', 'dirty': True, 'error': None}
        with TemporaryDirectory() as temp:
            hook = write_version_runtime_hook(Path(temp) / 'build', version)
            with patch.dict(sys.modules):
                sys.modules.pop('sharppy', None)
                sys.modules.pop('sharppy._version', None)
                exec(compile(hook.read_text(encoding='utf-8'), str(hook), 'exec'), {})
                module = sys.modules['sharppy._version']
                package = importlib.import_module('sharppy')
                self.assertEqual(package.__version__, version['version'])
                self.assertEqual(module.get_versions(), version)
                changed = module.get_versions()
                changed['version'] = 'changed'
                self.assertEqual(module.get_versions(), version)
        self.assertEqual(version_file.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
