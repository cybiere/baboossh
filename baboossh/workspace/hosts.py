from baboossh import Host


class HostsMixin:
    """`Workspace` methods for managing `Host` objects."""

    def host_del(self, host):
        """Remove a :class:`Host` from the workspace

        Args:
            name (str): The `Host` 's username
        """

        if host not in [host.name for host in Host.find_all()]:
            print("Not a known Host name.")
            return False
        host = Host.find_one(name=host)
        self.unstore(host.delete())
        return True

    def host_tag(self, host, tagname):
        """Add a :class:`Tag` to an :class:`Host`

        Args:
            host (str): the `Host` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            host = Host.find_one(name=host)
        except ValueError:
            print("Could not find host.")
            return False
        if host is None:
            print("Could not find host.")
            return False
        for endpoint in host.endpoints:
            endpoint.tag(tagname)
        return True

    def host_untag(self, host, tagname):
        """Remove a :class:`Tag` from an :class:`Host`

        Args:
            host (str): the `Host` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            host = Host.find_one(name=host)
        except ValueError:
            print("Could not find host.")
            return False
        if host is None:
            print("Could not find host.")
            return False
        for endpoint in host.endpoints:
            endpoint.untag(tagname)
        return True
