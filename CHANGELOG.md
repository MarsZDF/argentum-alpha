# Changelog

All notable changes to argentum will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [## [Unreleased]] - 2025-11-08

### Added

#### Core Features
- **StateDiff**: Track and analyze changes in agent state over time
  - Snapshot creation with labeled states
  - Diff computation between any two snapshots
  - Sequential change analysis across multiple states
  - Support for nested dictionaries and lists
  - Memory-efficient deep copying

- **Handoff**: Standardized protocol for agent-to-agent context transfer
  - Type-safe handoff creation with validation
  - JSON serialization/deserialization for network transfer
  - Receipt generation for acknowledgment workflows
  - Confidence tracking and artifact management
  - Framework-agnostic design

- **ContextDecay**: Temporal decay management for agent memory
  - Configurable exponential decay with custom half-life
  - Importance-based retention priorities
  - Active context filtering with thresholds
  - Automatic memory cleanup for long-running agents
  - Custom decay function support

- **PlanLinter**: Static analysis and validation of agent execution plans
  - Deterministic error detection (E001-E004) and warnings (W001-W003)
  - Tool reference validation with typo suggestions
  - Parameter validation against tool specifications
  - Circular dependency detection
  - Security scanning for exposed credentials
  - Auto-fix suggestions for common errors
  - SARIF output format for CI/CD integration

#### Infrastructure
- **Exception Handling**: Comprehensive custom exception hierarchy
  - Specific exceptions for each module with detailed context
  - Validation utilities for common parameter checks
  - Error wrapping for better debugging

- **Logging**: Structured logging with performance tracking
  - Colored console output with customizable formatters
  - Performance timing utilities
  - Debug logging for agent state transitions
  - Production and development configuration presets

- **Type Safety**: Full type hints with mypy compliance
  - py.typed marker for type checker recognition
  - Comprehensive type annotations across all modules
  - Optional dependency handling with graceful degradation

#### Developer Experience
- **Examples**: Real working examples for each module
  - Functional state tracking in query processing
  - Multi-agent content creation pipeline
  - Conversational AI memory management
  - ML pipeline plan validation

- **Testing**: Comprehensive test suite with performance benchmarks
  - 100% test coverage for core functionality
  - Performance tests and memory usage validation
  - Benchmark suite with pytest-benchmark integration
  - Edge case validation and error condition testing

- **Documentation**: Sphinx-based API documentation
  - Complete API reference with type information
  - Usage examples and tutorials
  - Performance optimization guides

- **CI/CD**: GitHub Actions workflow
  - Multi-platform testing (Linux, Windows, macOS)
  - Python 3.8-3.12 compatibility testing
  - Automated security scanning with bandit
  - Package building and validation
  - Optional dependency testing

- **Code Quality**: Pre-commit hooks and linting
  - Black code formatting
  - isort import sorting
  - flake8 style checking
  - mypy type checking
  - bandit security scanning
  - Automated testing on commit

### Installation Options
- Core package: `pip install argentum-agent`
- With plan linting: `pip install argentum-agent[lint]`
- Development: `pip install argentum-agent[dev]`
- All features: `pip install argentum-agent[all]`

### Dependencies
- **Core**: Python 3.8+ with minimal dependencies
- **Optional**: jsonschema, jsonpatch for enhanced plan linting
- **Development**: pytest, mypy, black, isort, flake8, pre-commit
- **Documentation**: sphinx, sphinx-rtd-theme, sphinx-autodoc-typehints