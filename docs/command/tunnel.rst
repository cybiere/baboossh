tunnel command
==============

Manage :class:`~baboossh.Tunnel` objects.

If no subcommand is provided, the default behaviour is `list`.

list
++++

List active tunnels in a tabular view.

open
++++

Open a SSH tunnel using a :class:`~baboossh.Endpoint` with a known :class:`~baboossh.Connection` as the output, and creates a SOCKS proxy on local port `<port>`. If no port is specified, a random available port is used.

Arguments
---------

 - `<connection>`: a connection from the workspace, given as a "<user>:#<credsId>@<ip>:<port>" string
 - `<port>`: an integer between 0 and 65535, indicating the port number the proxy will listen on the local host

close
+++++

Close the tunnel listening on local port `<port>`.

Arguments
---------

 - `<port>`: an integer between 0 and 65535 corresponding to the local port of the :class:`~baboossh.Tunnel` to close.
