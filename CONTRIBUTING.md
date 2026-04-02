# Contributing to MdMemory

Thank you for your interest in contributing to MdMemory! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/pvkarthikk/MdMemory.git
cd MdMemory

# Using uv (recommended)
uv sync

# Or using pip with dev dependencies
pip install -e ".[dev]"
```

## Code Standards

### Code Style
- Use [Black](https://github.com/psf/black) for code formatting (100 char line length)
- Use [Ruff](https://github.com/astral-sh/ruff) for linting
- Use [MyPy](https://www.mypy-lang.org/) for type checking

### Running Code Quality Checks

```bash
# Format code
black src/ tests/ example.py

# Lint
ruff check src/ tests/ example.py

# Type checking
mypy src/

# All checks
black src/ tests/ example.py && ruff check src/ tests/ example.py && mypy src/
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/mdmemory --cov-report=html

# Run specific test
pytest tests/test_mdmemory.py::TestMdMemory::test_store_creates_file -v
```

## Making Changes

1. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and ensure all tests pass:
   ```bash
   pytest tests/ -v
   ```

3. Format and lint your code:
   ```bash
   black src/ tests/ example.py
   ruff check src/ tests/ example.py --fix
   ```

4. Write or update tests as needed

5. Update documentation (README, docstrings, etc.)

6. Commit with clear, descriptive message:
   ```bash
   git commit -m "Add feature: clear description of changes"
   ```

7. Push to your fork and create a Pull Request

## Release Process

### Version Management

MdMemory follows [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for new functionality (backward compatible)
- PATCH version for bug fixes (backward compatible)

### Releasing a New Version

1. Update version in:
   - `pyproject.toml` (version field)
   - `src/mdmemory/__init__.py` (__version__)

2. Update `CHANGELOG.md` with new version and changes

3. Commit version bump:
   ```bash
   git commit -m "chore: bump version to X.Y.Z"
   ```

4. Tag the release:
   ```bash
   git tag -a vX.Y.Z -m "Release version X.Y.Z"
   git push origin vX.Y.Z
   ```

5. Build and publish to PyPI:
   ```bash
   # Build distribution
   uv build
   # or
   python -m build

   # Upload to PyPI (requires credentials)
   python -m twine upload dist/*
   ```

   Or using uv (if supported):
   ```bash
   uv publish
   ```

### Pre-release Checklist

- [ ] All tests passing: `pytest tests/ -v`
- [ ] Code formatted: `black src/ tests/ example.py`
- [ ] Linting clean: `ruff check src/ tests/ example.py`
- [ ] Type checking clean: `mypy src/`
- [ ] CHANGELOG.md updated
- [ ] Version numbers updated
- [ ] README.md current
- [ ] No uncommitted changes

## Building the Distribution

```bash
# Using uv
uv build

# Or using hatchling directly
python -m pip install hatchling
python -m hatchling build
```

This creates:
- `dist/mdmemory-X.Y.Z-py3-none-any.whl` (wheel)
- `dist/mdmemory-X.Y.Z.tar.gz` (source distribution)

## Pull Request Guidelines

- Describe what your PR addresses
- Link to any related issues
- Include test coverage for new features
- Ensure all CI checks pass
- Request review from maintainers

## Questions?

Feel free to:
- Open an issue on GitHub
- Check existing documentation
- Create a discussion for feature requests

Thank you for contributing to MdMemory! 🚀
