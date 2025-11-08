#!/bin/bash
# Automated version bumping script for Argentum

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if bump type is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 {patch|minor|major}"
    echo ""
    echo "Examples:"
    echo "  $0 patch   # 0.1.0 -> 0.1.1 (bug fixes)"
    echo "  $0 minor   # 0.1.0 -> 0.2.0 (new features)"
    echo "  $0 major   # 0.1.0 -> 1.0.0 (breaking changes)"
    exit 1
fi

BUMP_TYPE=$1

# Validate bump type
if [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major)$ ]]; then
    print_error "Invalid bump type: $BUMP_TYPE"
    print_error "Must be one of: patch, minor, major"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    print_warning "You have uncommitted changes:"
    git status --short
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Aborted due to uncommitted changes"
        exit 1
    fi
fi

# Get current version
CURRENT_VERSION=$(python -c "from argentum import __version__; print(__version__)")
print_status "Current version: $CURRENT_VERSION"

# Check if bump2version is installed
if ! command -v bump2version &> /dev/null; then
    print_error "bump2version is not installed"
    print_status "Installing bump2version..."
    pip install bump2version
fi

# Preview the version bump
NEW_VERSION=$(bump2version --dry-run --list $BUMP_TYPE | grep new_version | cut -d= -f2)
print_status "New version will be: $NEW_VERSION"

# Confirm the bump
echo ""
read -p "Bump version from $CURRENT_VERSION to $NEW_VERSION? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Version bump cancelled"
    exit 0
fi

# Run tests before bumping (optional)
echo ""
read -p "Run tests before bumping version? (Y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_status "Running tests..."
    if command -v pytest &> /dev/null; then
        pytest --quiet
        if [ $? -ne 0 ]; then
            print_error "Tests failed. Aborting version bump."
            exit 1
        fi
        print_success "Tests passed!"
    else
        print_warning "pytest not found, skipping tests"
    fi
fi

# Perform the version bump
print_status "Bumping version..."
bump2version $BUMP_TYPE

if [ $? -eq 0 ]; then
    print_success "Version bumped successfully!"
    print_success "New version: $NEW_VERSION"
    print_status "Git tag created: v$NEW_VERSION"
    
    # Show the git log
    echo ""
    print_status "Recent commits:"
    git log --oneline -3
    
    # Ask about pushing
    echo ""
    read -p "Push to remote repository? (Y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_status "Pushing to origin..."
        git push origin main --tags
        print_success "Pushed to remote repository with tags!"
    fi
    
    echo ""
    print_success "Version bump complete! 🚀"
    print_status "Consider updating the CHANGELOG.md with release notes"
else
    print_error "Version bump failed"
    exit 1
fi