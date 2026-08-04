from typing import TYPE_CHECKING, Protocol

from baboossh import Endpoint, Tag

if TYPE_CHECKING:
    class _Workspace(Protocol):
        options: dict[str, object]
        def unstore(self, data: dict[str, list[str]]) -> None: ...
        def set_option(self, option: str, value: str | None) -> None: ...

__all__ = ["EndpointsMixin"]


class EndpointsMixin:
    """`Workspace` methods for managing `Endpoint` objects."""

    #Manually add a endpoint
    def endpoint_add(self: "_Workspace", ipaddr: str, port: "int | str") -> None:
        """Add an :class:`Endpoint` to the workspace

        Args:
            ipaddr (str): the `Endpoint` 's IP address
            ipaddr (str): the `Endpoint` 's port
        """

        Endpoint(ipaddr, port).save()

    def endpoint_del(self: "_Workspace", endpoint: str) -> bool:
        """Remove an :class:`Endpoint` from the workspace

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
        """

        if endpoint[0] == "!":
            tag = Tag(endpoint[1:])
            for tagged_endpoint in tag.endpoints:
                self.unstore(tagged_endpoint.delete())
            return True
        try:
            found_endpoint = Endpoint.find_one(ip_port=endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if found_endpoint is None:
            print("Could not find endpoint.")
            return False
        if self.options["endpoint"] == found_endpoint:
            self.set_option("endpoint", None)
        self.unstore(found_endpoint.delete())
        return True

    def endpoint_tag(self: "_Workspace", endpoint: str, tagname: str) -> bool:
        """Add a :class:`Tag` to an :class:`Endpoint`

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            found_endpoint = Endpoint.find_one(ip_port=endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if found_endpoint is None:
            print("Could not find endpoint.")
            return False
        found_endpoint.tag(tagname)
        return True

    def endpoint_untag(self: "_Workspace", endpoint: str, tagname: str) -> bool:
        """Remove a :class:`Tag` from an :class:`Endpoint`

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            found_endpoint = Endpoint.find_one(ip_port=endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if found_endpoint is None:
            print("Could not find endpoint.")
            return False
        found_endpoint.untag(tagname)
        return True
