# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### CI/CD Pipeline
- GitHub Actions test workflow (`.github/workflows/tests.yml`)
  - Matrix testing for Python 3.9, 3.10, 3.11, 3.12
  - pytest with coverage reporting
  - Codecov integration for coverage tracking
- GitHub Actions code quality workflow (`.github/workflows/quality.yml`)
  - Ruff linting and format checking
  - mypy type checking (warnings only)
- Pre-commit configuration (`.pre-commit-config.yaml`)
  - Ruff lint and format hooks
  - Standard pre-commit hooks (trailing-whitespace, end-of-file-fixer, check-yaml)
- Codecov configuration (`codecov.yml`)
  - 80% coverage targets for project and patch
- Ruff configuration in `pyproject.toml`
  - Target Python 3.9+
  - Line length 100
  - Rules: E, W, F, I, B, UP

#### Expanded Test Suite
- New test files:
  - `tests/conftest.py` - 8 shared pytest fixtures
  - `tests/test_calibration.py` - 12 tests for StructuralCalibration
  - `tests/test_uncertainty.py` - 14 tests for UncertaintyAnalysis
  - `tests/test_numerical_accuracy.py` - 12 numerical validation tests
  - `tests/test_edge_cases.py` - 22 edge case and boundary tests
  - `tests/test_integration.py` - 10 complete workflow tests
- Added TestModalSuperposition class to `tests/test_analysis.py` (4 tests)
- Coverage configuration in `pyproject.toml`

### Changed
- Test count: 34 → 105 tests
- Code coverage: 42% → 85%
- Python version requirement: 3.8+ → 3.9+ (`requires-python` in `pyproject.toml` now matches)
- Updated README with CI badges
- README badges, clone URL and dashboard GitHub link now point at the real repository
- README shows dashboard screenshots and example result figures (`docs/images/`)
- Example result figures moved from the repository root and `output/` into `docs/images/`;
  `examples/run_workflow.py` now writes to `output/`, which is git-ignored
- Added `LICENSE` file (MIT)

### Fixed
- Python 3.9 import failure (`TypeError: unsupported operand type(s) for |`) caused by
  PEP 604 unions in modules without `from __future__ import annotations`
- Ruff lint errors (unused imports/variables, import sorting) and formatting in the
  prediction and dashboard modules that were failing the Code Quality workflow
- 43 ruff lint errors:
  - UP035/UP006: Deprecated typing imports (List→list, Dict→dict, Optional→X|None)
  - I001: Import sorting
  - B904: Exception chaining (raise ... from e)
- Code formatting standardized with ruff format

## [0.0.1] - 2026-01-19

### Added
- Initial release
- Core modules: building, ground_motion, analysis, calibration, uncertainty, visualization
- MDOFShearBuilding class for N-story shear building models
- Newmark-beta and modal superposition time integration
- Synthetic ground motion generation with Saragoni-Hart envelope
- StructuralCalibration for sensor-based model updating
- UncertaintyAnalysis for Monte Carlo propagation
- Visualization utilities including comprehensive results figure
- Example workflow script
- Initial test suite (34 tests)
