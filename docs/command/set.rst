set command
===========

Manage active :ref:`Workspace options`

If no subcommand is provided, the default behaviour is `list`.

list
++++

List current active options values.

<option>
++++++++

Set given `<value>` to one of the <option> : `endpoint`, `user`, `creds`, `payload` or `params`. If no `<value>` is given, set the value to `None`.

See :ref:`Workspace options` for details

Arguments
---------

 - `<value>`: a valid value for chosen `<option>` option.

Examples
--------

 - `set creds #1`: use :class:`~baboossh.Creds` with id 1 when trying to authenticate with :ref:`connect command` or :ref:`run command`.
 - `set endpoint !printServers`: Target the endpoints tagged with "printServers" :class:`~baboossh.Tag` when trying to connect with :ref:`probe command`, :ref:`connect command` or :ref:`run command`.
 - `set user`: Do not use a specific user, causing Baboosh to use any in-scope user when trying to authenticate with :ref:`connect command` or :ref:`run command`.
