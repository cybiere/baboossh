import os

WORKSPACES_DIR = os.path.join(os.path.expanduser("~"), ".baboossh")
BABOOSSH_VERSION = "1.1.1"

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

def is_workspace_compat(workspace_version):
    if BABOOSSH_VERSION == workspace_version:
        return True

    b_major, b_minor, b_patch = BABOOSSH_VERSION.split(".")
    w_major, w_minor, w_patch = workspace_version.split(".")
    if b_major == "1":
        if w_major != "1":
            return False
        if b_minor == "1":
            if w_minor in ["1", "2"]:
                return True
    return False
