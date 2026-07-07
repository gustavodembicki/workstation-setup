class WorkstationSetupError(Exception):
    """Base class for all errors raised by workstation-setup."""


class StepError(WorkstationSetupError):
    """Raised when a Step's install action fails.

    Carries the underlying command and stderr so the wizard can show the
    real cause instead of a bare traceback.
    """

    def __init__(self, message: str, *, command: list[str] | None = None, stderr: str = ""):
        super().__init__(message)
        self.command = command
        self.stderr = stderr


class AbortError(WorkstationSetupError):
    """Raised when the user chooses to stop the wizard after a failed step."""


class UnsupportedPlatformError(WorkstationSetupError):
    """Raised when an operation is requested on a platform that doesn't support it.

    E.g. a Homebrew cask install requested on Linux, where casks don't exist.
    """
