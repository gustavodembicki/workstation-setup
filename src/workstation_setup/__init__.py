try:
    # The release workflow creates this module immediately before PyInstaller
    # runs. Keeping it untracked means a CI build can carry its release tag
    # without changing the source version used by local development.
    from workstation_setup._build_version import __version__
except ModuleNotFoundError:
    __version__ = "0.1.0"
