host command
============

Manage :class:`~baboossh.Host` objects

If no subcommand is provided, the default behaviour is `list`.

list
++++

List hosts in workspace and their endpoints in a tabular view.

tag
+++

Add a :class:`~baboossh.Tag` to every :class:`~baboossh.Endpoint` of a :class:`~baboossh.Host`

Arguments
---------

 - `<name>`: the :class:`~baboossh.Host` name to which endpoints you want to add a tag to
 - `<tagname>`: the name of the :class:`~baboossh.Tag` to add. A "!" will be prepended to the name if it is not included.

untag
+++++

Remove a :class:`~baboossh.Tag` from every :class:`~baboossh.Endpoint` of a :class:`~baboossh.Host`

Arguments
---------

 - `<name>`: the :class:`~baboossh.Host` name to which endpoints you want to remove a tag from
 - `<tagname>`: the name of the :class:`~baboossh.Tag` to remove. A "!" will be prepended to the name if it is not included.


search
++++++

Search hosts whose name or uname match a pattern, and optionally tag the results.

Arguments
---------

 - `<search field>`: the field in which to perform the search.
 - `<value>`: the value to search for.

 - `-t <tag>, -\\-tag <tag>`: add the :class:`~baboossh.Tag` to every endpoint of every host in the search result


delete
++++++

Delete the Host object, and recursively delete any :class:`~baboossh.Path` starting from this Host.

Arguments
---------

 - `<host>`: a Host object name.

