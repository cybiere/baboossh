import os

BABOOSSH_VERSION = "1.1.0-dev"

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

def unstore_targets_merge(original, new_data):
    for obj_type, obj_list in new_data.items():
        if obj_type in original:
            original[obj_type] = [*original[obj_type], *obj_list]
        else:
            original[obj_type] = obj_list 
