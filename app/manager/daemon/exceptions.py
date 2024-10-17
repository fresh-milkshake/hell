class DaemonIsNotRunningError(Exception):
    def __init__(self, message='Daemon is not running'):
        super().__init__(message)


class DaemonIsRunningError(Exception):
    def __init__(self, message="Daemon is running"):
        super().__init__(message)


class RequirementsInstallationFailed(Exception):
    def __init__(self, message="Requirements installation failed"):
        super().__init__(message)
