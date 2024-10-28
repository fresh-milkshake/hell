import platform

if platform.system() == "Windows":
    from .windows import WindowsIsolationProvider
    IsolationProvider = WindowsIsolationProvider
else:
    from .linux import LinuxIsolationProvider
    IsolationProvider = LinuxIsolationProvider


__all__ = ["IsolationProvider"]