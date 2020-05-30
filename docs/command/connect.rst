Connect command
===============

Test provided parameters validity to establish a connection. If a connection is established, identifies the targeted ~baboossh.Endpoint's ~baboossh.Host.

Syntax
++++++

`connect [-v|--verbose] [-g|--gateway <gateway>] [<connection>]`

Arguments
---------

 - `<connection>`: A [Connection string]([Object]-Connection).
 - `<gateway>`: An [Endpoint]([Object]-Endpoint).

Options
-------

 - `-v|--verbose`: print every pivot while connecting
 - `-g|--gateway <gateway>`: force the use of `<gateway>` as the gateway to connect (instead of automatically calculated path)

If `<connection>` is provided, test it is working, eventually forcing specified `<gateway>`.

If `<connection>` is not provided, use the current [workspace options]([Object]-Workspace) to determine which [User]([Object]-User) and [Creds]([Object]-Creds) to connect to which [Endpoint]([Object]-Endpoint). If any of these option is not set, try every object in the workspace for the option until a connection is successfully established or all combinations are tested.

Examples
++++++++

Verbosity
---------

```
connect -v foo:#1@192.168.1.1:22
```

Test connecting to Endpoint `192.168.1.1:22` with User `foo` and Creds `#1`, printing every pivot performed.

Gateway
-------

```
connect -g 192.168.3.254:22 bar:#2@192.168.4.15:2222
```

Test connecting to endpoint `192.168.4.15:2222` using `192.168.3.254:22` as a gateway.

BabooSSH will find an existing working [Connection]([Object]-Connection) to `192.168.3.254:22`, connect to it and using it as a gateway will try to connect to `bar:#2@192.168.4.15:2222`

Workspace options
-----------------

```
set user baz
set endpoint 10.0.15.212:22
connect
```

As no creds have been specified, BabooSSH will sequentially attempt to connect with User `baz` to Endpoint `10.0.15.212:22` using every Creds object in the workspace, until a connection is successfully established or all creds are tested. Be careful as this could imply an important number of connection failures, resulting in locked account and alerts.

Spray
-----

`connect`: Without specifying any target either as an argument or in the workspace options, BabooSSH will attemp to log every User using every Creds on every Endpoint. Be careful as this could imply an important number of connection failures, resulting in locked account and alerts.

