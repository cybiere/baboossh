run command
===========

Run a payload on an open connection.

Syntax
++++++

`run [<target> <payload> [<parameters>...]]`

Arguments
---------

 - `<target>`: A :class:`~baboossh.Connection` , an :class:`~baboossh.Endpoint`, a :class:`~baboossh.Tag` or a :class:`~baboossh.Host` to run payload on
 - `<payload>`: A `Payload module` name.
 - `<parameters>`: Specified payload's parameters (if any).

If `<target>` is not provided, Baboossh will use the current :ref:`Workspace options` to determine which :class:`~baboossh.User` and :class:`~baboossh.Creds` to connect to which :class:`~baboossh.Endpoint`. If any of these option is not set, it will enumerate any working connection using specified parameters and run on them.

Options
-------

 - `-v|--verbose`: increase output verbosity

Examples
++++++++

Run payload on a Host
---------------------

```
run SRV-WEB2 exec cat /etc/passwd
```

Find a working connection to Host `SRV-WEB2` and run payload `exec` with parameters `cat /etc/passwd`

Using workspace options
-----------------------

```
set connection foo:#2@192.168.1.1:22
set payload shell
run
```

Run payload `shell` on connection `foo:#2@192.168.1.1:22` if it is working.

Spray
-----

```
set user root
set payload getfile
set params /etc/shadow
run
```

Run payload `getfile` with parameters `/etc/shadow` on every working connection with user `root`.
