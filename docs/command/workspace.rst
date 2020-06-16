workspace command
=================

Manage the :class:`~baboossh.Workspace`

Subcommands
+++++++++++

If no subcommand is provided, the default behaviour is `list`.

list
----

List existing workspaces. Current workspace is shown between brackets.

add
---

Create a new workspace and set it as current workspace.

Arguments
^^^^^^^^^

 - `<name>`: a string consisting of letters (upper and lower case), numbers and "-_."

use
---

Close current workspace and open workspace with provided name if it exists.

Arguments
+++++++++

 - `<name>`: the name of the workspace to open


delete
------

Delete a workspace. You cannot delete currently active workspace, you must first `use` another.

Deleting a workspace will delete its folder, including the database storing the objects and the loot folder containing keys and files fetched with BabooSSH.

Arguments
+++++++++

 - `<name>`: the name of the workspace to delete.

