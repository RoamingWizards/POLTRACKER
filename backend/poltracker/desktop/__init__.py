"""Native macOS app support: local paths, database bootstrap, background refresh, and the launcher.

Nothing in here is imported by the web API or the CLI tools, so the existing development workflow is unchanged.
"""

APP_NAME = "POLTRACKER"
APP_VERSION = "0.1.0"  # keep in sync with pyproject.toml (a test enforces it)
BUNDLE_IDENTIFIER = "com.roamingwizards.poltracker"
