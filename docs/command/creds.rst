creds command
=============

Manage :class:`~baboossh.Creds` objects

To get more information on credentials types, see :ref:`Authentication modules`.

If no subcommand is provided, the default behaviour is `list`.

list
++++

List credentials in workspace in a tabular view.

types
+++++

List available credentials types.

add
+++

Add creds to workspace

Arguments
---------

 - `<type>`: a credentials type
 - `[<values>...]`: depending on the credentials type, the parameters to build the Creds internal object

show
++++

Show the detail of a Creds internal object.

Arguments
---------

 - `<id>`: a Creds object ID.

edit
++++

Edit the Creds internal object data, depending on the credentials type.

Arguments
---------

 - `<id>`: a Creds object ID.

delete
++++++

Delete the Creds object, and recursively delete any :class:`~baboossh.Connection` object using these creds.

Arguments
---------

 - `<id>`: a Creds object ID.
