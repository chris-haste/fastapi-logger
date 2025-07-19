"""Tests for release guardrails functionality."""

import os
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from check_release_guardrails import (
    check_changelog_version,
    check_release_guardrails,
    extract_version_from_commit,
    get_pyproject_version,
)


class TestReleaseGuardrails:
    """Test release guardrails functionality."""

    def test_extract_version_from_commit_valid(self):
        """Test extracting version from valid release commit messages."""
        test_cases = [
            ("chore(release): v0.1.0", "0.1.0"),
            ("chore(release): v1.2.3", "1.2.3"),
            ("chore(release): v10.20.30", "10.20.30"),
        ]

        for commit_msg, expected_version in test_cases:
            result = extract_version_from_commit(commit_msg)
            assert result == expected_version

    def test_extract_version_from_commit_invalid(self):
        """Test extracting version from invalid commit messages."""
        invalid_commits = [
            "feat: add new feature",
            "chore(release): v0.1",  # Missing patch version
            "chore(release): v0.1.0.0",  # Too many version parts
            "chore(release): v0.1.0-beta",  # Pre-release not supported
            "chore(release): v0.1.0 ",  # Extra space
            " chore(release): v0.1.0",  # Leading space
            "chore(release): v0.1.0\n",  # Extra newline
        ]

        for commit_msg in invalid_commits:
            result = extract_version_from_commit(commit_msg)
            assert result is None

    def test_get_pyproject_version(self):
        """Test extracting version from pyproject.toml."""
        # This test uses the actual pyproject.toml file
        version = get_pyproject_version()
        assert version is not None
        assert isinstance(version, str)
        # Should be a valid semver format
        import re

        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(semver_pattern, version)

    def test_get_pyproject_version_missing_file(self, tmp_path):
        """Test handling missing pyproject.toml file."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with pytest.raises(FileNotFoundError, match="pyproject.toml not found"):
                get_pyproject_version()
        finally:
            os.chdir(original_cwd)

    def test_check_changelog_version(self):
        """Test checking version in CHANGELOG.md."""
        # Test with current version from pyproject.toml
        current_version = get_pyproject_version()
        assert check_changelog_version(current_version) is True

        # Test with non-existent version
        assert check_changelog_version("999.999.999") is False

    def test_check_changelog_version_missing_file(self, tmp_path):
        """Test handling missing CHANGELOG.md file."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            assert check_changelog_version("0.1.0") is False
        finally:
            os.chdir(original_cwd)

    def test_check_release_guardrails_not_release_commit(self):
        """Test guardrails check with non-release commit."""
        success, message = check_release_guardrails("feat: add new feature")
        assert success is True
        assert "Not a release commit" in message

    def test_check_release_guardrails_release_commit_success(self):
        """Test guardrails check with valid release commit."""
        # Test with current version from pyproject.toml
        current_version = get_pyproject_version()
        commit_msg = f"chore(release): v{current_version}"
        success, message = check_release_guardrails(commit_msg)
        assert success is True
        assert f"All checks passed for version {current_version}" in message

    def test_check_release_guardrails_version_mismatch(self):
        """Test guardrails check with version mismatch."""
        success, message = check_release_guardrails("chore(release): v999.999.999")
        assert success is False
        assert "Version mismatch" in message

    def test_check_release_guardrails_missing_changelog(self, tmp_path):
        """Test guardrails check with missing changelog entry."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create a minimal pyproject.toml
            with open("pyproject.toml", "w") as f:
                f.write('[project]\nversion = "0.1.0"\n')

            # Don't create CHANGELOG.md to simulate missing entry
            success, message = check_release_guardrails("chore(release): v0.1.0")
            assert success is False
            assert "not found in CHANGELOG.md" in message
        finally:
            os.chdir(original_cwd)

    def test_check_release_guardrails_with_commit_msg_param(self):
        """Test guardrails check with explicit commit message parameter."""
        current_version = get_pyproject_version()
        commit_msg = f"chore(release): v{current_version}"
        success, message = check_release_guardrails(commit_msg)
        assert success is True
        assert f"All checks passed for version {current_version}" in message

    def test_check_release_guardrails_without_commit_msg_param(self, monkeypatch):
        """Test guardrails check without commit message parameter."""

        # Mock git command to return a valid release commit
        def mock_git_log(*args, **kwargs):
            current_version = get_pyproject_version()

            class MockResult:
                def __init__(self):
                    self.stdout = f"chore(release): v{current_version}\n"
                    self.returncode = 0

                def check(self):
                    pass

            return MockResult()

        import subprocess

        monkeypatch.setattr(subprocess, "run", mock_git_log)

        current_version = get_pyproject_version()
        success, message = check_release_guardrails()
        assert success is True
        assert f"All checks passed for version {current_version}" in message

    def test_check_release_guardrails_git_failure(self, monkeypatch):
        """Test guardrails check when git command fails."""

        def mock_git_log(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "git log")

        import subprocess

        monkeypatch.setattr(subprocess, "run", mock_git_log)

        success, message = check_release_guardrails()
        assert success is False
        assert "Failed to get commit message from git" in message
