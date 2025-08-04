"""Tests for version management functionality."""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import fapilog


class TestVersionManagement:
    """Test version management functionality."""

    def test_version_attribute_exists(self):
        """Test that __version__ attribute exists and is a string."""
        assert hasattr(fapilog, "__version__")
        assert isinstance(fapilog.__version__, str)
        assert len(fapilog.__version__) > 0

    def test_version_format(self):
        """Test that version follows semantic versioning format."""
        import re

        version = fapilog.__version__
        # Should match semver pattern (x.y.z)
        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(semver_pattern, version), (
            f"Version {version} doesn't match semver pattern"
        )

    def test_version_from_metadata(self):
        """Test that version is read from package metadata."""
        # This should work in both installed and development environments
        version = fapilog.__version__
        assert version is not None
        assert isinstance(version, str)

    @patch("importlib.metadata.version")
    def test_version_fallback_to_pyproject(self, mock_version):
        """Test fallback to pyproject.toml when metadata is not available."""
        # Mock importlib.metadata.version to raise PackageNotFoundError
        mock_version.side_effect = importlib.metadata.PackageNotFoundError("fapilog")

        # Reload the module to test the fallback
        if "fapilog" in sys.modules:
            del sys.modules["fapilog"]

        import fapilog

        # Should still get a version (from pyproject.toml or fallback)
        assert hasattr(fapilog, "__version__")
        assert isinstance(fapilog.__version__, str)

    @patch("importlib.metadata.version")
    def test_version_fallback_with_import_error(self, mock_version):
        """Test fallback when importlib.metadata is not available."""
        # Mock importlib.metadata.version to raise ImportError
        mock_version.side_effect = ImportError("No module named 'importlib.metadata'")

        # Reload the module to test the fallback
        if "fapilog" in sys.modules:
            del sys.modules["fapilog"]

        import fapilog

        # Should still get a version (from pyproject.toml or fallback)
        assert hasattr(fapilog, "__version__")
        assert isinstance(fapilog.__version__, str)

    @patch("importlib.metadata.version")
    def test_version_fallback_with_attribute_error(self, mock_version):
        """Test fallback when importlib.metadata.version raises AttributeError."""
        # Mock importlib.metadata.version to raise AttributeError
        mock_version.side_effect = AttributeError(
            "'module' object has no attribute 'version'"
        )

        # Reload the module to test the fallback
        if "fapilog" in sys.modules:
            del sys.modules["fapilog"]

        import fapilog

        # Should still get a version (from pyproject.toml or fallback)
        assert hasattr(fapilog, "__version__")
        assert isinstance(fapilog.__version__, str)

    def test_version_consistency_with_pyproject(self):
        """Test that version is consistent with pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        # Read version from pyproject.toml
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            pyproject_version = data["project"]["version"]

        # Version should match (or be the fallback version if metadata differs)
        fapilog_version = fapilog.__version__

        # In development, they should match. In installed packages,
        # fapilog.__version__ comes from package metadata which reflects
        # the version at build time
        assert fapilog_version in [pyproject_version, "0.1.0", "0.1.2"]

    def test_version_in_all_list(self):
        """Test that __version__ is included in __all__."""
        assert "__version__" in fapilog.__all__

    def test_version_import_stability(self):
        """Test that importing fapilog multiple times doesn't change version."""
        # Clear module cache
        if "fapilog" in sys.modules:
            del sys.modules["fapilog"]

        # Import multiple times
        import fapilog

        version1 = fapilog.__version__

        if "fapilog" in sys.modules:
            del sys.modules["fapilog"]

        import fapilog

        version2 = fapilog.__version__

        # Versions should be consistent
        assert version1 == version2

    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_version_fallback_when_pyproject_missing(self, mock_open, mock_exists):
        """Test fallback when pyproject.toml is not found."""
        # Mock pyproject.toml to not exist
        mock_exists.return_value = False

        # Reload the module to test the fallback
        if "fapilog" in sys.modules:
            del sys.modules["fapilog"]

        import fapilog

        # Should get fallback version
        assert fapilog.__version__ in ["0.1.0", "0.1.2", "0.2.0", "unknown"]

    def test_version_in_development_environment(self):
        """Test version reading in development environment."""
        # This test verifies that version reading works in the current
        # development environment (editable install)
        version = fapilog.__version__
        assert version is not None
        assert isinstance(version, str)
        assert len(version) > 0

    def test_version_attributes_after_import(self):
        """Test that all expected attributes are available after import."""
        expected_attributes = [
            "__version__",
            "configure_logging",
            "create_logging_container",
            "get_logger",
            "get_current_trace_id",
            "log",
        ]

        for attr in expected_attributes:
            assert hasattr(fapilog, attr), f"Missing attribute: {attr}"

    def test_version_string_representation(self):
        """Test that version can be converted to string and used normally."""
        version = fapilog.__version__

        # Should work in string operations
        version_str = str(version)
        assert isinstance(version_str, str)
        assert len(version_str) > 0

        # Should work in f-strings
        version_fstring = f"Version: {version}"
        assert "Version: " in version_fstring
        assert version in version_fstring

    @patch("importlib.metadata.version")
    def test_version_fallback_tomli_import_error(self, mock_version):
        """Test fallback when both tomllib and tomli are not available."""
        # Mock importlib.metadata.version to raise PackageNotFoundError
        mock_version.side_effect = importlib.metadata.PackageNotFoundError("fapilog")

        # Mock tomllib import to fail
        with patch.dict("sys.modules", {"tomllib": None, "tomli": None}):
            # Reload the module to test the fallback
            if "fapilog" in sys.modules:
                del sys.modules["fapilog"]

            import fapilog

            # Should get fallback version
            assert fapilog.__version__ == "unknown"

    @patch("importlib.metadata.version")
    def test_version_fallback_tomli_import_error_with_tomli(self, mock_version):
        """Test fallback when tomllib fails but tomli is available."""
        # Mock importlib.metadata.version to raise PackageNotFoundError
        mock_version.side_effect = importlib.metadata.PackageNotFoundError("fapilog")

        # Mock tomllib import to fail but tomli to succeed
        with patch.dict("sys.modules", {"tomllib": None}):
            # Mock tomli module
            mock_tomli = MagicMock()
            mock_tomli.load.return_value = {"project": {"version": "0.2.0"}}

            with patch.dict("sys.modules", {"tomli": mock_tomli}):
                # Reload the module to test the fallback
                if "fapilog" in sys.modules:
                    del sys.modules["fapilog"]

                import fapilog

                # Should get version from tomli
                assert fapilog.__version__ == "0.2.0"

    @patch("importlib.metadata.version")
    def test_version_fallback_pyproject_key_error(self, mock_version):
        """Test fallback when pyproject.toml has invalid structure."""
        # Mock importlib.metadata.version to raise PackageNotFoundError
        mock_version.side_effect = importlib.metadata.PackageNotFoundError("fapilog")

        # Mock tomllib to return invalid data structure
        mock_tomllib = MagicMock()
        mock_tomllib.load.return_value = {"invalid": "structure"}

        with patch.dict("sys.modules", {"tomllib": mock_tomllib}):
            # Reload the module to test the fallback
            if "fapilog" in sys.modules:
                del sys.modules["fapilog"]

            import fapilog

            # Should get fallback version
            assert fapilog.__version__ == "unknown"

    @patch("importlib.metadata.version")
    def test_version_fallback_pyproject_os_error(self, mock_version):
        """Test fallback when pyproject.toml file cannot be read."""
        # Mock importlib.metadata.version to raise PackageNotFoundError
        mock_version.side_effect = importlib.metadata.PackageNotFoundError("fapilog")

        # Mock open to raise OSError
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # Reload the module to test the fallback
            if "fapilog" in sys.modules:
                del sys.modules["fapilog"]

            import fapilog

            # Should get fallback version
        assert fapilog.__version__ == "unknown"

    def test_get_logger_function(self):
        """Test the get_logger function."""
        logger = fapilog.get_logger()
        # structlog.get_logger returns a BoundLoggerLazyProxy, not BoundLogger
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")

        # Test with name parameter
        named_logger = fapilog.get_logger("test")
        assert hasattr(named_logger, "info")
        assert hasattr(named_logger, "error")
        assert hasattr(named_logger, "warning")
        assert hasattr(named_logger, "debug")

    def test_get_log_function(self):
        """Test the _get_log function for backward compatibility."""
        # Access the private function through the module
        from fapilog import _get_log

        logger = _get_log()
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")

    def test_create_logging_container_function(self):
        """Test the create_logging_container function."""
        # Test without settings
        container = fapilog.create_logging_container()
        assert container is not None

        # Test with settings
        from fapilog.config import LoggingSettings

        settings = LoggingSettings(level="DEBUG")
        container_with_settings = fapilog.create_logging_container(settings)
        assert container_with_settings is not None

    def test_log_proxy_attributes(self):
        """Test the log proxy object."""
        # Test that log proxy has expected methods
        assert hasattr(fapilog.log, "info")
        assert hasattr(fapilog.log, "error")
        assert hasattr(fapilog.log, "warning")
        assert hasattr(fapilog.log, "debug")

        # Test that methods are callable
        assert callable(fapilog.log.info)
        assert callable(fapilog.log.error)
        assert callable(fapilog.log.warning)
        assert callable(fapilog.log.debug)

    def test_log_proxy_method_calls(self):
        """Test that log proxy methods can be called without errors."""
        # These should not raise any exceptions
        fapilog.log.info("test message")
        fapilog.log.info("test with data", key="value", number=42)
        fapilog.log.error("test error", error_code=500)
        fapilog.log.warning("test warning", component="test")
        fapilog.log.debug("test debug", debug_info="test")

    def test_get_current_trace_id_import(self):
        """Test that get_current_trace_id is properly imported and accessible."""
        assert hasattr(fapilog, "get_current_trace_id")
        assert callable(fapilog.get_current_trace_id)

    def test_configure_logging_import(self):
        """Test that configure_logging is properly imported and accessible."""
        assert hasattr(fapilog, "configure_logging")
        assert callable(fapilog.configure_logging)

    def test_all_exports(self):
        """Test that all items in __all__ are properly exported."""
        for item_name in fapilog.__all__:
            assert hasattr(fapilog, item_name), f"Missing export: {item_name}"
            if item_name != "__version__":
                assert callable(getattr(fapilog, item_name)), (
                    f"Export not callable: {item_name}"
                )
