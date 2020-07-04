export command
==============

Export workspace data, using one of the :ref:`exporter extensions`.

Syntax
++++++

`export [<exporter> [<param>...]]`

Arguments
---------

 - `<exporter>`: the [export extension]([Extensions]-export) to use.
 - `<param>`: Parameters to provide to the export extension.

If  no `<exporter>` is provided, list available export extensions.

If `<exporter>` is provided, run the corresponding export extension providing it given `<param>`.

Examples
++++++++

List export extensions
----------------------

```
export
```

Export the compromission graph
------------------------------

See :ref:`comprom-graph exporter`.

```
export comprom-graph /tmp/graph.dot
```
