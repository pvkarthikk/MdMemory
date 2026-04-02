#!/bin/bash
# MdMemory Release Helper Script
# This script helps with building and releasing MdMemory to PyPI

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check Python version
check_python() {
    print_header "Checking Python Version"
    python --version
    print_success "Python version check passed"
}

# Run tests
run_tests() {
    print_header "Running Tests"
    if command -v uv &> /dev/null; then
        uv run pytest tests/ -v
    else
        pytest tests/ -v
    fi
    print_success "All tests passed"
}

# Check code quality
check_quality() {
    print_header "Checking Code Quality"
    
    echo "Running Black..."
    black src/ tests/ example.py --check 2>/dev/null || {
        print_warning "Code formatting issues found. Run: black src/ tests/ example.py"
        return 1
    }
    
    echo "Running Ruff..."
    ruff check src/ tests/ example.py 2>/dev/null || {
        print_warning "Linting issues found. Run: ruff check src/ tests/ example.py --fix"
        return 1
    }
    
    echo "Running MyPy..."
    mypy src/ 2>/dev/null || {
        print_warning "Type checking issues found"
        return 1
    }
    
    print_success "Code quality checks passed"
}

# Build distribution
build_distribution() {
    print_header "Building Distribution"
    
    # Clean previous builds
    rm -rf build dist *.egg-info
    
    # Build
    if command -v uv &> /dev/null; then
        echo "Building with uv..."
        uv build
    else
        echo "Building with python -m build..."
        python -m build
    fi
    
    print_success "Distribution built successfully"
    echo "Files created:"
    ls -lh dist/
}

# Display package info
show_info() {
    print_header "Package Information"
    
    # Get version from pyproject.toml
    VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "//' | sed 's/"//')
    
    echo "Package: mdmemory"
    echo "Version: $VERSION"
    echo "License: MIT"
    echo "Python: >=3.9"
    echo ""
    echo "Repository: https://github.com/pvkarthikk/MdMemory"
    echo "PyPI: https://pypi.org/project/mdmemory/"
}

# Main help
print_help() {
    echo "Usage: ./release.sh [command]"
    echo ""
    echo "Commands:"
    echo "  check          Run all checks (tests + code quality)"
    echo "  build          Build distribution package"
    echo "  test           Run tests only"
    echo "  quality        Check code quality only"
    echo "  info           Show package information"
    echo "  clean          Clean build artifacts"
    echo "  help           Show this help message"
    echo ""
    echo "PyPI Release Process:"
    echo "  1. Update version in pyproject.toml and src/mdmemory/__init__.py"
    echo "  2. Update CHANGELOG.md with new version"
    echo "  3. Run: ./release.sh check"
    echo "  4. Run: ./release.sh build"
    echo "  5. Run: python -m twine upload dist/*"
    echo ""
    echo "Example:"
    echo "  ./release.sh check && ./release.sh build"
}

# Clean build artifacts
clean() {
    print_header "Cleaning Build Artifacts"
    rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
    print_success "Cleaned successfully"
}

# Main script
case "${1:-help}" in
    check)
        check_python
        run_tests
        check_quality
        print_success "All checks passed! Ready to build."
        ;;
    build)
        build_distribution
        ;;
    test)
        run_tests
        ;;
    quality)
        check_quality
        ;;
    info)
        show_info
        ;;
    clean)
        clean
        ;;
    help)
        print_help
        ;;
    *)
        echo "Unknown command: $1"
        print_help
        exit 1
        ;;
esac
