tag command
===========

Manage :class:`~baboossh.Tag` objects.

If no subcommand is provided, the default behaviour is `list`.

list
++++

List existing tags in a tabular view.

show
++++

List tag members

Arguments
---------

 - `<tagname>`: the name of the :class:`~baboossh.Tag` to display. A "!" will be prepended to the name if it is not included.

delete
++++++

Delete a :class:`~baboossh.Tag` by removing it from all endpoints

Arguments
---------

 - `<tagname>`: the name of the :class:`~baboossh.Tag` to delete. A "!" will be prepended to the name if it is not included.
