# Changelog

All notable changes to this project will be documented in this file.

The format is based on *Keep a Changelog*, and this project adheres to *Semantic Versioning*.

## [Unreleased]

### Added
- Thin CLI entrypoint with argparse subcommands (`udp`, `radio`, `swarm`).
- Centralized environment-backed configuration loader (`src/config/__init__.py`).
- Core runner scaffold to orchestrate application lifecycle (`src/core/runner.py`).

### Changed
- CLI is now responsible for parsing args and constructing Settings (no direct hardware wiring in CLI).

### Fixed
- N/A

### Removed
- N/A
