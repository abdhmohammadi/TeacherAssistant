# Automatic Versioning System

The Teacher Assistant project uses an automatic versioning system that supports semantic versioning (major.minor.patch).

## How It Works

The versioning system automatically determines the version using the following priority:

1. **Git Tags** (highest priority)
   - If the project is in a Git repository, the version is automatically extracted from the latest Git tag
   - Tags should follow semantic versioning format: `v1.2.3` or `1.2.3`
   - If no tags exist, it uses commit count as patch version (e.g., `0.0.42`)

2. **VERSION File** (fallback)
   - If Git is not available, the system reads from the `VERSION` file in the project root
   - This file contains a single line with the version number (e.g., `0.2.8`)

3. **Default Version** (last resort)
   - If neither Git nor VERSION file is available, it falls back to the default version in `version.py`

## Usage

### Getting the Current Version

The version is automatically available in your code:

```python
from version import __version__

print(f"Current version: {__version__}")
```

### Getting Detailed Version Information

```python
from version import get_version_info

info = get_version_info()
print(f"Version: {info['version']}")
print(f"Source: {info['source']}")  # 'git', 'file', or 'default'
print(f"Git available: {info['git_available']}")
print(f"Git commit: {info['git_commit']}")
```

### Bumping Versions

Use the `version_bump.py` script to increment the version:

```bash
# Bump patch version (0.2.8 -> 0.2.9)
python scripts/version_bump.py patch

# Bump minor version (0.2.8 -> 0.3.0)
python scripts/version_bump.py minor

# Bump major version (0.2.8 -> 1.0.0)
python scripts/version_bump.py major

# Bump and create Git tag
python scripts/version_bump.py patch --tag

# Bump with custom tag message
python scripts/version_bump.py minor --tag --message "Release v0.3.0"
```

## Semantic Versioning

The project follows [Semantic Versioning](https://semver.org/) (SemVer):

- **MAJOR** version: Increment when you make incompatible API changes
- **MINOR** version: Increment when you add functionality in a backward compatible manner
- **PATCH** version: Increment when you make backward compatible bug fixes

## Workflow

### For Regular Development

1. Make your changes
2. Commit your changes
3. When ready to release, bump the version:
   ```bash
   python scripts/version_bump.py patch --tag
   ```
4. Push the tag to remote:
   ```bash
   git push --tags
   ```

### For Releases

1. Decide on the version bump type (major/minor/patch)
2. Run the bump script with `--tag` flag:
   ```bash
   python scripts/version_bump.py minor --tag --message "Release v0.3.0"
   ```
3. The script will:
   - Update the `VERSION` file
   - Update `version.py` default version
   - Create a Git tag (if `--tag` is used)
4. Push the tag:
   ```bash
   git push --tags
   ```

## Files

- `src/teacher_assistant/version.py` - Main version module with automatic detection
- `VERSION` - Fallback version file (should be tracked in Git)
- `scripts/version_bump.py` - Script for bumping versions

## Notes

- The `VERSION` file should be committed to Git as it serves as a fallback
- Git tags are the preferred method for versioning
- The version is automatically displayed in the application window title
- The versioning system works even when Git is not available (uses VERSION file)

