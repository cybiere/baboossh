from typing import TYPE_CHECKING, Protocol

from baboossh import Host

if TYPE_CHECKING:
    class _Workspace(Protocol):
        def unstore(self, data: dict[str, list[str]]) -> None: ...

__all__ = ["HostsMixin"]


class HostsMixin:
    """`Workspace` methods for managing `Host` objects."""

    def host_del(self: "_Workspace", host: str) -> bool:
        """Remove a :class:`Host` from the workspace

        Args:
            name (str): The `Host` 's username
        """

        if host not in [h.name for h in Host.find_all()]:
            print("Not a known Host name.")
            return False
        found_host = Host.find_one(name=host)
        if found_host is None:
            print("Could not find host.")
            return False
        self.unstore(found_host.delete())
        return True

    def host_tag(self: "_Workspace", host: str, tagname: str) -> bool:
        """Add a :class:`Tag` to an :class:`Host`

        Args:
            host (str): the `Host` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            found_host = Host.find_one(name=host)
        except ValueError:
            print("Could not find host.")
            return False
        if found_host is None:
            print("Could not find host.")
            return False
        for endpoint in found_host.endpoints:
            endpoint.tag(tagname)
        return True

    def host_untag(self: "_Workspace", host: str, tagname: str) -> bool:
        """Remove a :class:`Tag` from an :class:`Host`

        Args:
            host (str): the `Host` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            found_host = Host.find_one(name=host)
        except ValueError:
            print("Could not find host.")
            return False
        if found_host is None:
            print("Could not find host.")
            return False
        for endpoint in found_host.endpoints:
            endpoint.untag(tagname)
        return True
