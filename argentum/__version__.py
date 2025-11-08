"""Version information for argentum package."""

__version__ = "0.2.1"
__version_info__ = (0, 1, 0)

# Semantic version components
MAJOR = 0
MINOR = 1
PATCH = 0

# Build information
BUILD = None
PRERELEASE = None

def get_version(build: bool = False) -> str:
    """
    Get the version string for argentum.
    
    Args:
        build: Include build information if available
        
    Returns:
        Version string in semantic versioning format
        
    Examples:
        >>> get_version()
        '0.1.0'
        >>> get_version(build=True)
        '0.1.0+build.123' # if BUILD is set
    """
    version = f"{MAJOR}.{MINOR}.{PATCH}"
    
    if PRERELEASE:
        version += f"-{PRERELEASE}"
    
    if build and BUILD:
        version += f"+{BUILD}"
    
    return version

# Compatibility with common version checking patterns
VERSION = __version__