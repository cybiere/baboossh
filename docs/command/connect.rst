connect command
===============

Test provided parameters validity to establish a connection. If a connection is established, identifies the targeted :class:`~baboossh.Endpoint` 's :class:`~baboossh.Host`.

Syntax
++++++

`connect [-v|-\\-verbose] [-f|-\\-force] [-p,-\\-probe] [<connection>]`

Arguments
---------

 - `<connection>`: A :class:`~baboossh.Connection` to target.

Options
-------

 - `-v|-\\-verbose`: increase output verbosity
 - `-p|-\\-probe`: if the target endpoint has not been probed (using :ref:`probe command`) yet, connection is refused. Setting this flag will automatically probe the endpoint before connecting to it.
 - `-f|-\\-force`: in order to decrease the noise, connections are not run if they are already know to be working. Setting this flag will force running the connection.

If `<connection>` is not provided, Baboossh will use the current :ref:`Workspace options` to determine which :class:`~baboossh.User` and :class:`~baboossh.Creds` to connect to which :class:`~baboossh.Endpoint`. If any of these option is not set, try every object in the scope for the option until a connection is successfully established or all combinations are tested.

Examples
++++++++

Verbosity
---------

```
connect -v foo:#1@192.168.1.1:22
```

Test connecting to Endpoint `192.168.1.1:22` with User `foo` and Creds `#1`, printing every pivot performed.

Using workspace options
-----------------------

```
set user baz
set endpoint 10.0.15.212:22
connect
```

As no creds have been specified, BabooSSH will sequentially attempt to connect with User `baz` to Endpoint `10.0.15.212:22` using every Creds object in scope, until a connection is successfully established or all creds are tested. Be careful as this could imply an important number of connection failures, resulting in locked account and alerts.

Spray
-----

`connect`: Without specifying any target either as an argument or in the workspace options, BabooSSH will attemp to log every User using every Creds on every Endpoint. Be careful as this could imply an important number of connection failures, resulting in locked accounts and alerts.

