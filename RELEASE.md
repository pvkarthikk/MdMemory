# MdMemory Release Guide

This document describes the process for releasing MdMemory to PyPI.

## Prerequisites

- Python 3.9+
- Git access to repository
- PyPI account (https://pypi.org)
- PyPI API token stored in `~/.pypirc` or environment

## Installation of Release Tools

```bash
pip install build twine
```

Or with uv:
```bash
uv pip install build twine
```

## Release Checklist

### 1. Prepare Release

- [ ] Ensure all tests pass: `pytest tests/ -v`
- [ ] Code is formatted: `black src/ tests/ example.py`
- [ ] Linting passes: `ruff check src/ tests/ example.py`
- [ ] Type checking passes: `mypy src/`
- [ ] No uncommitted changes: `git status`

### 2. Update Version Numbers

Update version in both files to maintain consistency:

**File: `pyproject.toml`**
```toml
[project]
name = "mdmemory"
version = "0.X.Y"  # Update this
```

**File: `src/mdmemory/__init__.py`**
```python
__version__ = "0.X.Y"  # Update this
```

Use [Semantic Versioning](https://semver.org/):
- `0.1.0` → `0.2.0` for new features (MINOR)
- `0.1.0` → `0.1.1` for bug fixes (PATCH)
- `0.1.0` → `1.0.0` for breaking changes (MAJOR)

### 3. Update Changelog

Edit `CHANGELOG.md` and add a new section for the version:

```markdown
## [0.X.Y] - YYYY-MM-DD

### Added
- New feature 1
- New feature 2

### Changed
- Changed feature 1

### Fixed
- Bug fix 1
- Bug fix 2

### Removed
- Removed feature 1
```

Use the [Keep a Changelog](https://keepachangelog.com/) format.

### 4. Commit and Tag

```bash
# Commit version changes
git add pyproject.toml src/mdmemory/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 0.X.Y"

# Create annotated tag
git tag -a v0.X.Y -m "Release version 0.X.Y"

# Push commits and tag
git push origin main
git push origin v0.X.Y
```

### 5. Build Distribution

```bash
# Using the release helper script
./release.sh check    # Run all checks
./release.sh build    # Build distributions

# Or manually
python -m build
```

This creates:
- `dist/mdmemory-0.X.Y-py3-none-any.whl` (wheel)
- `dist/mdmemory-0.X.Y.tar.gz` (source distribution)

### 6. Verify Distribution

```bash
# Check wheel contents
unzip -l dist/mdmemory-0.X.Y-py3-none-any.whl

# Check metadata
unzip -p dist/mdmemory-0.X.Y-py3-none-any.whl "mdmemory-0.X.Y.dist-info/METADATA"

# Test install (optional)
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate
pip install dist/mdmemory-0.X.Y-py3-none-any.whl
python -c "import mdmemory; print(mdmemory.__version__)"
deactivate
rm -rf test_env
```

### 7. Setup PyPI Credentials

**Option A: Using `.pypirc` file**

Create `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # Your PyPI API token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # Your TestPyPI API token
```

**Option B: Using environment variable**

```bash
export TWINE_PASSWORD="pypi-AgEIcHlwaS5vcmc..."
export TWINE_USERNAME="__token__"
```

### 8. Test Upload (Optional but Recommended)

Upload to TestPyPI first to verify everything works:

```bash
python -m twine upload --repository testpypi dist/*

# Verify installation from TestPyPI
python -m pip install --index-url https://test.pypi.org/simple/ mdmemory==0.X.Y
```

### 9. Upload to PyPI

```bash
# Upload to PyPI
python -m twine upload dist/*

# Verify installation
pip install --upgrade mdmemory
python -c "import mdmemory; print(f'Version: {mdmemory.__version__}')"
```

### 10. Post-Release

- [ ] Verify package on PyPI: https://pypi.org/project/mdmemory/
- [ ] Check GitHub releases: https://github.com/pvkarthikk/MdMemory/releases
- [ ] Update project website/documentation if applicable
- [ ] Announce release on relevant channels

## Automated Release with Scripts

```bash
# Run complete release process
./release.sh check      # ✅ All checks pass
./release.sh build      # ✅ Distribution built
python -m twine upload dist/*  # ✅ Upload to PyPI
```

## Troubleshooting

### Build Issues

```bash
# Clean and rebuild
./release.sh clean
./release.sh build
```

### Upload Issues

```bash
# Check credentials
python -m twine --version

# Test upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Verbose upload for debugging
python -m twine upload -v dist/*
```

### Version Conflicts

If PyPI rejects version as already existing:
- Check if version was already released
- Increment version number
- Update files again
- Rebuild and retry

## Security

- Never commit PyPI tokens to git
- Use API tokens, not passwords
- Keep `~/.pypirc` file with restricted permissions: `chmod 600 ~/.pypirc`
- Rotate tokens periodically

## Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

## Questions?

Contact maintainers or open an issue on GitHub.
