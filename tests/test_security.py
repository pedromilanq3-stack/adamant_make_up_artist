import tempfile
import unittest
from pathlib import Path
from zipfile import ZipInfo

from instagram_archive.security import safe_member_path, validate_member


class SecurityTests(unittest.TestCase):
    def test_absolute_windows_and_parent_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for name in ("/etc/passwd", "C:/Windows/file.json", "safe/../../escape.json", "..\\escape.json"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    safe_member_path(ZipInfo(name), Path(directory))

    def test_unexpected_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                validate_member(ZipInfo("messages/data.sqlite"), Path(directory))

