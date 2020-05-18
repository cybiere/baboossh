import os

home = os.path.expanduser("~")
workspacesDir = os.path.join(home, ".baboossh")

class Unique(type):
    def __call__(cls, *args, **kwargs):
        from baboossh.workspace import Workspace
        if Workspace.active is None:
            raise ValueError("Cannot create an object out of a workspace")
        workspace = Workspace.active
        obj_id = cls.get_id(*args, **kwargs)
        if obj_id not in workspace.store[cls.__name__]:
            self = cls.__new__(cls, *args, **kwargs)
            cls.__init__(self, *args, **kwargs)
            workspace.store[cls.__name__][obj_id] = self
        return workspace.store[cls.__name__][obj_id]

    def __init__(cls, name, bases, attributes):
        super().__init__(name, bases, attributes)


