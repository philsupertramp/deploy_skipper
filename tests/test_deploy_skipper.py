import unittest
from parameterized import parameterized
from unittest import TestCase, mock
from pathlib import Path
import subprocess

from deploy_skipper import (
    load_patterns,
    matches_dir_star,
    posix_match,
    changed_files,
    latest_tag,
    normalize_path,
    path_matches_any,
    is_ignored,
)


class TestDeploySkipper(unittest.TestCase):
    def test_load_patterns(self):
        file_mock = mock.Mock(
            exists=mock.Mock(return_value=True),
            read_text=mock.Mock(return_value=mock.Mock(
                splitlines=mock.Mock(return_value='''
# comment
*.png
!myfile.txt
./dir/*
!.foo.py
! 
./
!./dir/file.py'''.split('\n')
            )))
        )
        blacklist, whitelist = load_patterns(file_mock)
        self.assertIn("*.png", blacklist)
        self.assertIn("dir/*", blacklist)  # normalized
        self.assertIn("myfile.txt", whitelist)
        self.assertIn("dir/file.py", whitelist)
        self.assertIn(".foo.py", whitelist)

    def test_load_patterns_failure_missing_file(self):
        file_mock = mock.Mock(exists=mock.Mock(return_value=False))

        with self.assertRaises(Exception) as ex:
            with mock.patch('deploy_skipper.sys') as sys_mock:
                sys_mock.side_effect = Exception('foo')
                load_patterns(file_mock)

            sys_mock.exist.assert_called_once_with(2)

    @parameterized.expand([
        ("dir/file.py", "dir/*", True),
        ("dir", "dir/*", True),
        ("dir/sub/file.py", "dir/*", True),
        ("dir/sub/file.py", "dir/**", False),  # handled by posix_match
        ("file.py", "dir/*", False),
    ])
    def test_matches_dir_star(self, file_path, pattern, expected):
        self.assertEqual(matches_dir_star(file_path, pattern), expected)

    @parameterized.expand([
        ("src/file.py", "src/*", True),
        ("src/sub/file.py", "src/*", True),
        ("src/sub/file.py", "src/**", True),
        ("README.md", "*.md", True),
        ("README.txt", "*.md", False),
    ])
    def test_posix_match(self, file_path, pattern, expected):
        matches = posix_match(file_path, pattern)
        self.assertEqual(matches, expected, matches)

    def test_posix_match_failes_for_pure_posix(self):
        with self.assertRaises(TypeError):
            matches = posix_match('src/file.py', 12)
            self.assertEqual(matches, False)

    @mock.patch("subprocess.run")
    def test_changed_files_success(self, mock_run):
        mock_run.return_value.stdout = "file1.txt\nfile2.py\n"
        mock_run.return_value.returncode = 0
        files = changed_files("HEAD~1")
        self.assertEqual(files, ["file1.txt", "file2.py"])
        mock_run.assert_called_once()

    @mock.patch("subprocess.run")
    def test_changed_files_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        with self.assertRaises(SystemExit) as cm:
            changed_files("HEAD~1")
        self.assertEqual(cm.exception.code, 2)

    @mock.patch("subprocess.check_output")
    def test_latest_tag_success(self, mock_check):
        mock_check.return_value = "v1.2.3\n"
        tag = latest_tag()
        self.assertEqual(tag, "v1.2.3")

    @mock.patch("subprocess.check_output")
    def test_latest_tag_failure(self, mock_check):
        mock_check.side_effect = subprocess.CalledProcessError(1, "git")
        with self.assertRaises(SystemExit) as cm:
            latest_tag()
        self.assertEqual(cm.exception.code, 2)

    @parameterized.expand([
        ("./file.txt", "file.txt"),
        ("file.txt", "file.txt"),
        ("./dir/file.py", "dir/file.py"),
        ("dir/file.py", "dir/file.py"),
    ])
    def test_normalize_path(self, path, expected):
        self.assertEqual(normalize_path(path), expected)

    @parameterized.expand([
        ("myfile.txt", ["*.txt"], "*.txt"),
        ("dir/file.py", ["dir/*"], "dir/*"),
        ("dir/sub/file.py", ["dir/**"], "dir/**"),
        ("README.md", ["*.md"], "*.md"),
        ("README.md", ["*.txt"], None),
    ])
    def test_path_matches_any(self, file_path, patterns, expected_match):
        match = path_matches_any(file_path, patterns)
        self.assertEqual(match, expected_match)

    @parameterized.expand([
        ("myfile.txt", ["*.txt"], [], True),
        ("myfile.txt", [], ["myfile.txt"], False),
        ("myfile.txt", ["*.txt"], ["myfile.txt"], False),  # whitelist wins
        ("image.png", ["*.png"], [], True),
        ("image.png", ["*.jpg"], [], False),
        ("dir/file.py", ["dir/*"], [], True),
        ("dir/file.py", ["dir/*"], ["dir/file.py"], False),
        ("dir/sub/file.py", ["dir/**"], [], True),
        ("dir/sub/file.py", ["dir/**"], ["dir/sub/file.py"], False),
        ("README.md", ["*.md"], ["README.md"], False),
        ("README.md", ["*.md"], [], True),
    ])
    def test_is_ignored(self, file_path, blacklist, whitelist, expected_ignored):
        ignored, _, _ = is_ignored(file_path, blacklist, whitelist)
        self.assertEqual(ignored, expected_ignored)


if __name__ == "__main__":
    unittest.main()
