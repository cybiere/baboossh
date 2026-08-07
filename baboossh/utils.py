import os
from typing import Any, Protocol, TypeVar

from baboossh.version import BABOOSSH_VERSION

WORKSPACES_DIR = os.path.join(os.path.expanduser("~"), ".baboossh")

class _UniqueInstance(Protocol):
    @classmethod
    def get_id(cls, *args: Any, **kwargs: Any) -> str: ...
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

_T = TypeVar("_T", bound=_UniqueInstance)

class Unique(type):
    def __call__(cls: type[_T], *args: Any, **kwargs: Any) -> _T:
        from baboossh.workspace import Workspace
        if Workspace.active is None:
            raise ValueError("Cannot create an object out of a workspace")
        workspace = Workspace.active
        obj_id = cls.get_id(*args, **kwargs)
        cached = workspace.store[cls.__name__].get(obj_id)
        if cached is None:
            cached = cls.__new__(cls)
            cls.__init__(cached, *args, **kwargs)
            workspace.store[cls.__name__][obj_id] = cached
        assert isinstance(cached, cls)
        return cached

    def __init__(cls, name: str, bases: tuple[type, ...], attributes: dict[str, object]) -> None:
        super().__init__(name, bases, attributes)

def unstore_targets_merge(original: dict[str, list[str]], new_data: dict[str, list[str]]) -> None:
    for obj_type, obj_list in new_data.items():
        if obj_type in original:
            original[obj_type] = [*original[obj_type], *obj_list]
        else:
            original[obj_type] = obj_list

def is_workspace_compat(workspace_version: str) -> bool:
    if BABOOSSH_VERSION == workspace_version:
        return True

    b_major, b_minor, b_patch = BABOOSSH_VERSION.split(".")
    w_major, w_minor, w_patch = workspace_version.split(".")
    if b_major == w_major:
        if b_minor == w_minor:
            return True
    return False
