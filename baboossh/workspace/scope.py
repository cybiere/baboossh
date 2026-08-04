from typing import TYPE_CHECKING, Protocol

from baboossh import Creds, Endpoint, Host, User

__all__ = ["ScopeMixin"]

if TYPE_CHECKING:
    class _Workspace(Protocol):
        def identify_object(self, target: str) -> "Creds | User | Endpoint | Host | None": ...


class ScopeMixin:
    """`Workspace` methods for identifying objects and toggling scope."""

    def identify_object(self, target: str) -> "Creds | User | Endpoint | Host | None":
        if target[0] == "#":
            creds_id = target[1:]
        else:
            creds_id = target
        creds = Creds.find_one(creds_id=creds_id)
        if creds is not None:
            return creds
        user = User.find_one(name=target)
        if user is not None:
            return user
        try:
            dst = Endpoint.find_one(ip_port=target)
            if dst is not None:
                return dst
        except ValueError:
            pass
        host = Host.find_one(name=target)
        if host is not None:
            return host
        print("Could not identify object.")
        return None

    def scope(self: "_Workspace", target: str) -> None:
        obj = self.identify_object(target)
        if obj is None:
            return
        obj.scope = not obj.scope
        obj.save()
