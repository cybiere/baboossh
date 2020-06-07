class NoPathError(Exception):
    """Raised when no path could be found to the target"""

class NoHostError(Exception):
    """Raised when not :class:`Host` exists"""

class ConnectionClosedError(Exception):
    """Raised when trying to use a closed :class:`Connection`"""

class WorkspaceVersionError(Exception):
    """Raised when a workspace was created using an incompatible version of BabooSSH"""

    def __init__(self, baboossh_ver, workspace_ver):
        self.baboossh_ver = baboossh_ver
        self.workspace_ver = workspace_ver
        super().__init__()


    def __str__(self):
        return "This workspace was created using BabooSSH v"+self.workspace_ver+" which is incompatible with current version (v"+self.baboossh_ver+")"
