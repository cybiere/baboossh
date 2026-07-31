from baboossh import Endpoint, Tag


class EndpointsMixin:
    """`Workspace` methods for managing `Endpoint` objects."""

    #Manually add a endpoint
    def endpoint_add(self, ipaddr, port):
        """Add an :class:`Endpoint` to the workspace

        Args:
            ipaddr (str): the `Endpoint` 's IP address
            ipaddr (str): the `Endpoint` 's port
        """

        Endpoint(ipaddr, port).save()

    def endpoint_del(self, endpoint):
        """Remove an :class:`Endpoint` from the workspace

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
        """

        if endpoint[0] == "!":
            tag = Tag(endpoint[1:])
            for endpoint in tag.endpoints:
                self.unstore(endpoint.delete())
            return True
        try:
            endpoint = Endpoint.find_one(ip_port=endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if endpoint is None:
            print("Could not find endpoint.")
            return False
        if self.options["endpoint"] == endpoint:
            self.set_option("endpoint", None)
        self.unstore(endpoint.delete())
        return True

    def endpoint_tag(self, endpoint, tagname):
        """Add a :class:`Tag` to an :class:`Endpoint`

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            endpoint = Endpoint.find_one(ip_port=endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if endpoint is None:
            print("Could not find endpoint.")
            return False
        endpoint.tag(tagname)
        return True

    def endpoint_untag(self, endpoint, tagname):
        """Remove a :class:`Tag` from an :class:`Endpoint`

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            endpoint = Endpoint.find_one(ip_port=endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if endpoint is None:
            print("Could not find endpoint.")
            return False
        endpoint.untag(tagname)
        return True
