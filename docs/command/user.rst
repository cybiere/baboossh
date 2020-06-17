user command
============

Manage :class:`~baboossh.User` objects

If no subcommand is provided, the default behaviour is `list`.

list
++++

List users in workspace in a tabular view.

Arguments
---------

 - `-a, -\\-all`: include out of scope users

add
+++

Add user `<name>` to the workspace.

Arguments
---------

 - `<name>`: the name of the user to add

delete
++++++

Delete the :class:`~baboossh.User` object from the :class:`~baboossh.Workspace`, and recursively delete any :class:`~baboossh.Connection` objects using this user.

Arguments
---------

 - `<name>`: an existing user name.
