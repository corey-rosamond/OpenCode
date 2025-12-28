"""Code-Forge - AI-powered CLI development assistant."""

try:
    from importlib.metadata import version

    __version__ = version("code-forge")
except Exception:
    __version__ = "0.0.0"  # Fallback for development/testing

__all__ = ["__version__"]
