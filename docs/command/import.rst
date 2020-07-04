import command
==============

Import data in workspace, using one of the :ref:`importer modules`. 

Syntax
++++++

`import [<importer> [<param>...]]`

Arguments
---------

 - `<importer>`: the [import extension]([Extensions]-import) to use.
 - `<param>`: Parameters to provide to the import extension.

If  no `<importer>` is provided, list available import extensions.

If `<importer>` is provided, run the corresponding import extension providing it given `<param>`.

Examples
++++++++

List importer extensions
------------------------

```
import
```

Import nmap scan results
------------------------

```
import nmap-xml /tmp/nmapout.xml
```
