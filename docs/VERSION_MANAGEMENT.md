# Version Management Guide

This document explains how to manage versions in the Argentum project using automated tools.

## 🚀 Quick Start

### Using Make Commands (Recommended)
```bash
# Patch version (bug fixes): 0.1.0 -> 0.1.1
make bump-patch

# Minor version (new features): 0.1.0 -> 0.2.0  
make bump-minor

# Major version (breaking changes): 0.1.0 -> 1.0.0
make bump-major
```

### Using Python Script
```bash
# Interactive version bumping with all safety checks
python scripts/version_manager.py minor

# Quick bump without tests (for hotfixes)
python scripts/version_manager.py patch --no-tests --no-commit
```

### Using Shell Script
```bash
# Simple bash script with prompts
./scripts/bump_version.sh minor
```

### Using bump2version directly
```bash
# Install if not available
pip install bump2version

# Bump version
bump2version patch  # or minor, major
```

## 🔧 Version Bumping Tools

### 1. Smart Python Version Manager (`scripts/version_manager.py`)
**Best for: Interactive development**

**Features:**
- ✅ Semantic version parsing and validation
- ✅ Automatic file updates (pyproject.toml, __version__.py, CHANGELOG.md)
- ✅ Git integration with commits and tags
- ✅ Test execution before bumping
- ✅ Safety checks and confirmations
- ✅ Colored output and progress indicators

**Usage:**
```bash
# Interactive bump with all safety checks
python scripts/version_manager.py minor

# Skip tests for quick hotfixes
python scripts/version_manager.py patch --no-tests

# Skip git operations (manual commit later)
python scripts/version_manager.py minor --no-commit
```

### 2. Bash Script (`scripts/bump_version.sh`)
**Best for: Simple automation**

**Features:**
- ✅ Simple and fast
- ✅ Interactive confirmations
- ✅ Git integration
- ✅ Test execution
- ✅ Colored output

**Usage:**
```bash
./scripts/bump_version.sh patch   # Bug fixes
./scripts/bump_version.sh minor   # New features  
./scripts/bump_version.sh major   # Breaking changes
```

### 3. GitHub Actions (`.github/workflows/version-bump.yml`)
**Best for: Team environments**

**Features:**
- ✅ Manual trigger from GitHub UI
- ✅ Automatic pull request creation
- ✅ Draft release creation
- ✅ Test execution in CI environment
- ✅ Team review process

**Usage:**
1. Go to GitHub Actions tab
2. Select "Automated Version Bump" workflow
3. Click "Run workflow" 
4. Choose bump type (patch/minor/major)
5. Review and merge the created PR

### 4. Make Commands (Makefile)
**Best for: Development workflow integration**

**Features:**
- ✅ Simple commands
- ✅ Integrated with other dev tasks
- ✅ Uses the smart Python version manager

**Usage:**
```bash
make bump-patch    # Bug fixes
make bump-minor    # New features
make bump-major    # Breaking changes

# Quick release workflow
make release       # Run all checks
make bump-minor    # Bump and commit
make git-push      # Push with tags
```

## 📋 Version Bump Workflow

### Standard Release Process

1. **Prepare for release:**
   ```bash
   make check  # Run tests, linting, security scans
   ```

2. **Bump version:**
   ```bash
   make bump-minor  # Choose appropriate bump type
   ```

3. **Push to remote:**
   ```bash
   git push origin main --tags
   ```

4. **Create GitHub release:**
   - Go to GitHub releases page
   - Create release from the new tag
   - Add release notes

### Hotfix Process

1. **Quick patch without full testing:**
   ```bash
   make bump-patch-quick
   ```

2. **Push immediately:**
   ```bash
   git push origin main --tags
   ```

### Team Release Process (GitHub Actions)

1. **Trigger workflow:**
   - GitHub Actions → "Automated Version Bump" → Run workflow

2. **Review PR:**
   - Review the generated pull request
   - Check version changes
   - Merge when ready

3. **Complete release:**
   - Edit the draft release
   - Add release notes  
   - Publish release

## 🎯 Semantic Versioning Rules

### Patch (0.1.0 → 0.1.1)
**When to use:** Bug fixes, security patches, documentation updates
```bash
make bump-patch
```

**Examples:**
- Fix webhook validation bug
- Update security documentation
- Correct typos in README

### Minor (0.1.0 → 0.2.0)
**When to use:** New features, enhancements, non-breaking changes
```bash
make bump-minor
```

**Examples:**
- Add cost alert webhooks
- New export formats
- Additional configuration options

### Major (0.1.0 → 1.0.0)
**When to use:** Breaking API changes, major refactors
```bash
make bump-major
```

**Examples:**
- Change function signatures
- Remove deprecated features
- Major architectural changes

## 🔧 Configuration Files

### `.bumpversion.cfg`
Configure bump2version behavior:
- Version file locations
- Commit and tagging settings
- Message templates

### `.github/workflows/version-bump.yml`
GitHub Actions workflow for team version management:
- Automated PR creation
- Test execution
- Draft release creation

### `Makefile`
Development workflow integration:
- Simple commands for common tasks
- Integration with version management

## 🚨 Troubleshooting

### "Tests failed" error
```bash
# Run tests manually to see failures
pytest -v

# Skip tests for emergency hotfixes
python scripts/version_manager.py patch --no-tests
```

### "Uncommitted changes" warning
```bash
# Check what's uncommitted
git status

# Commit changes first, or force bump
python scripts/version_manager.py minor  # Will prompt to continue
```

### "bump2version not found"
```bash
# Install bump2version
pip install bump2version

# Or use the Python script instead
python scripts/version_manager.py minor
```

### Version mismatch between files
```bash
# Reset to consistent state
git checkout HEAD -- pyproject.toml argentum/__version__.py

# Run bump again
make bump-patch
```

## 💡 Best Practices

1. **Always run tests before releasing:**
   ```bash
   make check  # Comprehensive checks
   ```

2. **Use descriptive commit messages:**
   The tools automatically generate good commit messages like:
   ```
   Bump version: 0.1.0 → 0.2.0
   ```

3. **Tag releases consistently:**
   All tools create tags in the format `v0.2.0`

4. **Update CHANGELOG.md:**
   The tools automatically add version entries, but manually add release notes:
   ```markdown
   ## [0.2.0] - 2024-11-08
   
   ### Added
   - Cost alert webhooks for Slack, Discord, Teams
   - Export functionality for CSV, Excel, PDF
   - Shareable dashboard URLs
   
   ### Security
   - Comprehensive webhook URL validation
   - Path traversal protection for exports
   - Message template injection prevention
   ```

5. **Use GitHub releases:**
   Create releases with detailed notes for each version

## 🔗 Related Commands

```bash
# Check current version
python -c "from argentum import __version__; print(__version__)"

# View version history
git tag -l | sort -V

# Compare versions
git log v0.1.0..v0.2.0 --oneline
```