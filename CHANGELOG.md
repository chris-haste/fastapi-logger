# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Baseline unit tests with comprehensive coverage for core functionality
- Coverage gate enforcing minimum 85% test coverage threshold
- GitHub Actions CI workflow with automated test execution
- Expanded test suite covering import/bootstrap path, settings validation, and processor pipeline
- Test coverage reporting with HTML and terminal output

### Changed

- Enhanced test_import.py with actual log.info call testing
- Improved test organization and coverage reporting

### Fixed

- None

### Removed

- None

## [0.1.0] - 2024-01-01

### Added

- Initial release of fapilog library
- Core logging functionality with structured JSON output
- FastAPI middleware integration
- Configurable sinks (stdout, loki)
- Environment-based configuration
- Pydantic V2 settings management
