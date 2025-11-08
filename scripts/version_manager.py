#!/usr/bin/env python3
"""
Smart version management script for Argentum.

This script provides intelligent version bumping with:
- Semantic version parsing and validation
- Automatic changelog updates
- Git integration
- Safety checks and confirmations
"""

import re
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional

# ANSI color codes for pretty output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

def print_status(message: str) -> None:
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

def print_success(message: str) -> None:
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def print_error(message: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def print_header(message: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BOLD}{Colors.BLUE} {message.center(58)} {Colors.NC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.NC}\n")

class SemanticVersion:
    """Handle semantic version parsing and manipulation."""
    
    def __init__(self, version_string: str):
        self.raw = version_string
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$', version_string)
        if not match:
            raise ValueError(f"Invalid semantic version: {version_string}")
        
        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))
        self.prerelease = match.group(4)
        self.build = match.group(5)
    
    def bump(self, bump_type: str) -> 'SemanticVersion':
        """Create a new version with the specified bump type."""
        if bump_type == 'major':
            return SemanticVersion(f"{self.major + 1}.0.0")
        elif bump_type == 'minor':
            return SemanticVersion(f"{self.major}.{self.minor + 1}.0")
        elif bump_type == 'patch':
            return SemanticVersion(f"{self.major}.{self.minor}.{self.patch + 1}")
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")
    
    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

class VersionManager:
    """Manage version bumping for Argentum project."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_file = project_root / "pyproject.toml"
        self.version_file = project_root / "argentum" / "__version__.py"
        self.changelog_file = project_root / "CHANGELOG.md"
    
    def get_current_version(self) -> SemanticVersion:
        """Get the current version from __version__.py."""
        try:
            if not self.version_file.exists():
                raise FileNotFoundError(f"Version file not found: {self.version_file}")
            
            content = self.version_file.read_text()
            match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
            if not match:
                raise ValueError("Could not parse version from __version__.py")
            
            return SemanticVersion(match.group(1))
        except Exception as e:
            print_error(f"Failed to get current version: {e}")
            sys.exit(1)
    
    def update_version_files(self, new_version: SemanticVersion) -> None:
        """Update version in all relevant files."""
        # Update pyproject.toml
        if self.pyproject_file.exists():
            content = self.pyproject_file.read_text()
            updated = re.sub(
                r'version = "[^"]+"',
                f'version = "{new_version}"',
                content
            )
            self.pyproject_file.write_text(updated)
            print_success(f"Updated {self.pyproject_file.name}")
        
        # Update __version__.py
        content = self.version_file.read_text()
        updated = re.sub(
            r'__version__ = ["\'][^"\']+["\']',
            f'__version__ = "{new_version}"',
            content
        )
        self.version_file.write_text(updated)
        print_success(f"Updated {self.version_file.name}")
    
    def update_changelog(self, new_version: SemanticVersion) -> None:
        """Update CHANGELOG.md with new version entry."""
        if not self.changelog_file.exists():
            print_warning("CHANGELOG.md not found, skipping changelog update")
            return
        
        content = self.changelog_file.read_text()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Add new version entry after [Unreleased]
        updated = re.sub(
            r'(## \[Unreleased\])',
            f'\\1\n\n## [{new_version}] - {today}',
            content
        )
        
        self.changelog_file.write_text(updated)
        print_success(f"Updated {self.changelog_file.name}")
    
    def check_git_status(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, check=True)
            return len(result.stdout.strip()) == 0
        except subprocess.CalledProcessError:
            print_warning("Not in a git repository or git not available")
            return True  # Allow non-git usage
    
    def run_tests(self) -> bool:
        """Run the test suite."""
        print_status("Running tests...")
        try:
            result = subprocess.run(['pytest', '--quiet'], check=True)
            return True
        except subprocess.CalledProcessError:
            print_error("Tests failed")
            return False
        except FileNotFoundError:
            print_warning("pytest not found, skipping tests")
            return True
    
    def create_git_commit_and_tag(self, old_version: SemanticVersion, 
                                 new_version: SemanticVersion) -> None:
        """Create git commit and tag for the version bump."""
        try:
            # Stage files
            files_to_stage = [
                str(self.pyproject_file.relative_to(self.project_root)),
                str(self.version_file.relative_to(self.project_root)),
            ]
            if self.changelog_file.exists():
                files_to_stage.append(str(self.changelog_file.relative_to(self.project_root)))
            
            subprocess.run(['git', 'add'] + files_to_stage, check=True)
            
            # Create commit
            commit_message = f"Bump version: {old_version} → {new_version}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            print_success(f"Created git commit: {commit_message}")
            
            # Create tag
            tag_name = f"v{new_version}"
            subprocess.run(['git', 'tag', '-a', tag_name, '-m', f"Release {new_version}"], check=True)
            print_success(f"Created git tag: {tag_name}")
            
        except subprocess.CalledProcessError as e:
            print_error(f"Git operation failed: {e}")
            sys.exit(1)
    
    def bump_version(self, bump_type: str, run_tests: bool = True, 
                    auto_commit: bool = True) -> None:
        """Main version bump workflow."""
        print_header(f"Argentum Version Bump ({bump_type.upper()})")
        
        # Get current version
        current_version = self.get_current_version()
        new_version = current_version.bump(bump_type)
        
        print_status(f"Current version: {Colors.BOLD}{current_version}{Colors.NC}")
        print_status(f"New version: {Colors.BOLD}{new_version}{Colors.NC}")
        
        # Check git status
        if auto_commit and not self.check_git_status():
            print_warning("You have uncommitted changes:")
            subprocess.run(['git', 'status', '--short'])
            if not self._confirm("Continue anyway?"):
                print_error("Aborted due to uncommitted changes")
                sys.exit(1)
        
        # Run tests
        if run_tests and not self.run_tests():
            if not self._confirm("Tests failed. Continue anyway?"):
                print_error("Aborted due to test failures")
                sys.exit(1)
        
        # Final confirmation
        print_status(f"\nReady to bump version from {current_version} to {new_version}")
        if not self._confirm("Proceed with version bump?"):
            print_warning("Version bump cancelled")
            sys.exit(0)
        
        # Update files
        print_status("\nUpdating version files...")
        self.update_version_files(new_version)
        self.update_changelog(new_version)
        
        # Git operations
        if auto_commit:
            self.create_git_commit_and_tag(current_version, new_version)
        
        print_success(f"\n🚀 Version bumped successfully to {new_version}!")
        
        if auto_commit:
            print_status("\nNext steps:")
            print_status("- Review the changes with: git show")
            print_status("- Push to remote with: git push origin main --tags")
            print_status("- Create a GitHub release from the new tag")
    
    def _confirm(self, question: str) -> bool:
        """Ask for user confirmation."""
        response = input(f"{question} (y/N): ").strip().lower()
        return response in ['y', 'yes']

def main():
    parser = argparse.ArgumentParser(
        description="Smart version management for Argentum",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python version_manager.py patch      # Bug fixes: 0.1.0 -> 0.1.1
  python version_manager.py minor      # New features: 0.1.0 -> 0.2.0  
  python version_manager.py major      # Breaking changes: 0.1.0 -> 1.0.0
  python version_manager.py minor --no-tests --no-commit
        """
    )
    
    parser.add_argument(
        'bump_type',
        choices=['patch', 'minor', 'major'],
        help='Type of version bump to perform'
    )
    
    parser.add_argument(
        '--no-tests',
        action='store_true',
        help='Skip running tests before bumping version'
    )
    
    parser.add_argument(
        '--no-commit',
        action='store_true', 
        help='Skip creating git commit and tag'
    )
    
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path.cwd(),
        help='Path to project root directory'
    )
    
    args = parser.parse_args()
    
    # Initialize version manager
    vm = VersionManager(args.project_root)
    
    # Perform version bump
    vm.bump_version(
        bump_type=args.bump_type,
        run_tests=not args.no_tests,
        auto_commit=not args.no_commit
    )

if __name__ == '__main__':
    main()