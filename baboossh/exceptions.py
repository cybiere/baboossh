class NoPathError(Exception):
    """Raised when no path could be found to the target"""

class NoHostError(Exception):
    """Raised when not :class:`Host` exists"""

class ConnectionClosedError(Exception):
    """Raised when trying to use a closed :class:`Connection`"""
