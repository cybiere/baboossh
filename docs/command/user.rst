user
====

Manage :class:`~baboossh.User` objects

Subcommands
+++++++++++

If no subcommand is provided, the default behaviour is `list`.

list
----

List users in workspace in a tabular view.

add
---

Arguments
^^^^^^^^^

 - `<name>`: a string

Add user `<name>` to the workspace.

delete
------

Arguments
^^^^^^^^^

 - `<name>`: an existing user name.

Delete the :class:`~baboossh.User` object from the :class:`~baboossh.Workspace`, and recursively delete any :class:`~baboossh.Connection` objects using this user.
