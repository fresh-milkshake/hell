from .windows import WindowsIsolationProvider
from .linux import LinuxIsolationProvider
import platform

if platform.system() == "Windows":
    IsolationProvider = WindowsIsolationProvider
else:
    IsolationProvider = LinuxIsolationProvider


__all__ = ["IsolationProvider"]