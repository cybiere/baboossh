path command
============

Manage :class:`~baboossh.Path` objects

If no subcommand is provided, the default behaviour is `list`.

list
++++

List paths in workspace in a tabular view.

Arguments
---------

 - `-a, -\\-all`: include out of scope hosts

add
+++

Create a :class:`~baboossh.Path` fron `<src>` to `<dst>`. This does not imply the destination endpoint becomes reachable, you must test it with the :ref:`probe command`

Arguments
---------

 - `<src>`: a :class:`~baboossh.Host` from the workspace or "Local"
 - `<dst>`: an :class:`~baboossh.Endpoint` from the workspace

get
+++

Show the shortest Path chain from "Local" to the provided :class:`~baboossh.Endpoint` or a :class:`~baboossh.Host`.

Arguments
---------

 - `<dst>`: an :class:`~baboossh.Endpoint` or a :class:`~baboossh.Host` from the workspace
 - `-n, -\\-numeric`: show each pivot with the :class:`~baboossh.Endpoint` instead of the :class:`~baboossh.Host`

delete
++++++

Delete a Path fron `<src>` to `<dst>` from the workspace.

Arguments
---------

 - `<src>`: a :class:`~baboossh.Host` from the workspace or "Local"
 - `<dst>`: an :class:`~baboossh.Endpoint` from the workspace

