"""
Automatic versioning system for Teacher Assistant.

This module automatically determines the version from Git tags if available,
or falls back to a stored version file. Supports semantic versioning (major.minor.patch).

Version detection priority:
1. Git tags (if git is available and repository exists)
2. VERSION file (if git is not available)
3. Fallback to default version
"""

import os
import re
import subprocess
from pathlib import Path

# Default fallback version
_DEFAULT_VERSION = "0.2.8"

# Get the project root directory (assuming this file is in src/teacher_assistant/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_VERSION_FILE = _PROJECT_ROOT / "VERSION"


def _get_version_from_git() -> str | None:
    """
    Get version from Git tags.
    Returns the latest tag if available, or None if git is not available.
    """
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return None

        # Get the latest tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            tag = result.stdout.strip()
            # Remove 'v' prefix if present (e.g., v1.0.0 -> 1.0.0)
            tag = tag.lstrip('v')
            # Validate version format (semantic versioning)
            if re.match(r'^\d+\.\d+\.\d+', tag):
                return tag
        
        # If no tags exist, check if we can get version from commit count
        # This creates a version like 0.0.1, 0.0.2, etc. based on commits
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            commit_count = result.stdout.strip()
            if commit_count.isdigit():
                # Use commit count as patch version
                return f"0.0.{commit_count}"
        
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        # Git is not available or command failed
        return None


def _get_version_from_file() -> str | None:
    """
    Get version from VERSION file.
    Returns the version string if file exists, None otherwise.
    """
    if _VERSION_FILE.exists():
        try:
            version = _VERSION_FILE.read_text(encoding='utf-8').strip()
            # Validate version format
            if re.match(r'^\d+\.\d+\.\d+', version):
                return version
        except (IOError, OSError):
            pass
    return None


def _save_version_to_file(version: str) -> None:
    """
    Save version to VERSION file.
    """
    try:
        _VERSION_FILE.write_text(version, encoding='utf-8')
    except (IOError, OSError):
        # If we can't write, that's okay - we'll just use git tags
        pass


def _get_version() -> str:
    """
    Get the current version using the priority order:
    1. Git tags
    2. VERSION file
    3. Default version
    """
    # Try git first
    version = _get_version_from_git()
    if version:
        # Update VERSION file with git version for consistency
        _save_version_to_file(version)
        return version
    
    # Try VERSION file
    version = _get_version_from_file()
    if version:
        return version
    
    # Fallback to default
    return _DEFAULT_VERSION


# Get and export the version
__version__ = _get_version()


def get_version_info() -> dict:
    """
    Get detailed version information.
    
    Returns:
        dict: Version information including:
            - version: The version string
            - source: Where the version came from ('git', 'file', or 'default')
            - git_available: Whether git is available
            - git_commit: Current git commit hash (if available)
    """
    info = {
        'version': __version__,
        'source': 'default',
        'git_available': False,
        'git_commit': None
    }
    
    # Check git availability
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info['git_available'] = True
            
            # Get current commit hash
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=_PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info['git_commit'] = result.stdout.strip()
            
            # Check if version came from git
            if _get_version_from_git():
                info['source'] = 'git'
                return info
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    # Check if version came from file
    if _get_version_from_file():
        info['source'] = 'file'
    
    return info
