"""Shared typed base classes for baboossh/ext_dir/*.py extension plugins.

Every ext_dir/*.py file must still define a class literally named
``BaboosshExt`` -- ``Extensions.load()`` discovers plugins by that exact
name via ``inspect.getmembers()`` (see baboossh/extensions.py). Plugins
should subclass the appropriate kind-specific base below instead of
redefining the metaclass boilerplate locally.
"""
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from baboossh import Connection, Workspace

__all__ = [
    "BaboosshExtMeta",
    "BaboosshExtBase",
    "BaboosshAuthBase",
    "BaboosshPayloadBase",
    "BaboosshImportExportBase",
]


class BaboosshExtMeta(ABCMeta):
    """Metaclass giving extension classes a readable str() (their registry key).

    ``getKey`` is declared here only so pyright can type-check ``__str__``'s
    body -- a metaclass method's ``cls`` parameter type-checks against the
    metaclass itself, not against classes using it as ``metaclass=``. At
    runtime this is never actually called: a concrete subclass's own
    ``getKey`` classmethod is found first in normal class-attribute lookup.
    """

    def getKey(cls) -> str:
        raise NotImplementedError

    def __str__(cls) -> str:
        return cls.getKey()


class BaboosshExtBase(metaclass=BaboosshExtMeta):
    """Base for all baboossh/ext_dir/ extension plugins.

    Only the surface that is genuinely identical across every plugin kind
    (auth/payload/import/export) lives here.
    """

    @classmethod
    @abstractmethod
    def getModType(cls) -> str:
        """Return the registry group: "auth"/"payload"/"export"/"import"."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def getKey(cls) -> str:
        """Return the extension's registry key."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def descr(cls) -> str:
        """Return a human-readable description of the extension."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def buildParser(cls, parser) -> None:
        """Add this extension's arguments to a cmd2 argparse parser."""
        raise NotImplementedError


class BaboosshAuthBase(BaboosshExtBase):
    """Base for auth_password.py / auth_privkey.py."""

    def __init__(self, creds: str) -> None:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def fromStatement(cls, stmt) -> str:
        """Build a serialized creds string from a parsed cmd2 statement."""
        raise NotImplementedError

    @abstractmethod
    def serialize(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def auth(self, username: str, transport) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def identifier(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def toList(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def show(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def edit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> None:
        raise NotImplementedError


class BaboosshPayloadBase(BaboosshExtBase):
    """Base for payload_exec.py, payload_gather.py, payload_getfile.py,
    payload_putfile.py, payload_shell.py."""

    @classmethod
    @abstractmethod
    def run(cls, connection: "Connection", wspaceFolder: str, stmt) -> bool:
        raise NotImplementedError


class BaboosshImportExportBase(BaboosshExtBase):
    """Base for export_comprograph.py, import_nmapxml.py, import-textlist.py."""

    @classmethod
    @abstractmethod
    def run(cls, stmt, workspace: "Workspace") -> bool:
        raise NotImplementedError
