class NoPathError(Exception):
    """Raised when no path could be found to the target"""
    pass

class NoHostError(Exception):
    """Raised when not :class:`Host` exists"""
    pass

class ConnectionClosedError(Exception):
    """Raised when trying to use a closed :class:`Connection`"""
    pass
