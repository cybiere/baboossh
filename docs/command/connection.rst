connection command
==================

Manage :class:`~baboossh.Connection` objects

If no subcommand is provided, the default behaviour is `list`.

list
++++

List connections in workspace in a tabular view.

Arguments
---------

 - `-a, -\\-all`: include out of scope connections 

close
+++++

Manually close an Connection opened with `connect command` or `run command` or as a gateway by one of those. Recursively closes any :class:`~baboossh.Connection` or :class:`~baboossh.Tunnel` using the connection as a pivot or an output.

Arguments
---------

 - `<connection>`: a connection from the workspace, given as a "<user>:#<credsId>@<ip>:<port>" string

delete
++++++

Delete a Connection from the workspace. If the deleted connection is the last to a given host, all :class:`Path` objects using this host will be deleted.

Arguments
---------

 - `<connection>`: a connection from the workspace, given as a "<user>:#<credsId>@<ip>:<port>" string
