endpoint command
================

Manage :class:`~baboossh.Endpoint` objects

Subcommands
+++++++++++

If no subcommand is provided, the default behaviour is `list`.

list
----

List endpoints in workspace in a tabular view.

add
---

Add endpoint `<ip>:<port>` to the workspace. If port is not specified, default value is 22.

Arguments
^^^^^^^^^

 - `<ip>`: a valid IPv4 or IPv6 IP address.
 - `<port>`: an integer between 0 and 65535. Default is 22

tag
---

Add a :class:`~baboossh.Tag` to an :class:`~baboossh.Endpoint`

Arguments
^^^^^^^^^

 - `<endpoint>`: the :class:`~baboossh.Endpoint` to add a tag to, given as a `<ip>:<port>` string
 - `<tagname>`: the name of the :class:`~baboossh.Tag` to add. A "!" will be prepended to the name if it is not included.

untag
-----

Remove a :class:`~baboossh.Tag` from an :class:`~baboossh.Endpoint`

Arguments
^^^^^^^^^

 - `<endpoint>`: the :class:`~baboossh.Endpoint` to remove the tag from, given as a `<ip>:<port>` string
 - `<tagname>`: the name of the :class:`~baboossh.Tag` to remove. A "!" will be prepended to the name if it is not included.


search
------

Search endpoints whose IP or Port match a pattern, and optionally tag the results.

Arguments
^^^^^^^^^

 - `<search field>`: the field in which to perform the search.
 - `<value>`: the value to search for.

 - `-a, -\\-all`: include out of scope endpoints in the search results
 - `-t <tag>, -\\-tag <tag>`: add the :class:`~baboossh.Tag` to every endpoint in the search result

delete
------

Delete the endpoint :class:`~baboossh.Endpoint` from the :class:`~baboossh.Workspace`. Recursively deletes :class:`~baboossh.Path`  and :class:`~baboossh.Connection` to the endpoint, as well as associated :class:`~baboossh.Host` if the Endpoint was the last to its Host.

Arguments
^^^^^^^^^

 - `<endpoint>`: a registered endpoint in the workspace, given as a `<ip>:<port>` string

