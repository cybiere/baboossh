probe command
=============

Test if an endpoint is reachable using stored paths or provided gateway, and saves the :class:`~baboossh.Endpoint` distance from local

Syntax
++++++

`probe [-v|-\\-verbose] [-a|-\\-again] [-n|-\\-new] [-g|-\\-gateway <gateway>] [<endpoint>]`

Arguments
---------

 - `<gateway>`: A :class:`~baboossh.Host` to use as gateway.
 - `<endpoint>`: An :class:`~baboossh.Endpoint` or a :class:`~baboossh.Tag` to reach.

Options
-------

 - `-v|-\\-verbose`: increase output verbosity
 - `-g|-\\-gateway <gateway>`: force the use of `<gateway>` as the gateway to connect (instead of automatically calculated path)
 - `-a|-\\-again`: include already probed endpoints
 - `-n|-\\-new`: try finding a new shorter path


If `<endpoint>` is provided, test if it is reachable, eventually forcing specified `<gateway>`. See :ref:`Path finding`.

If `<endpoint>` is not provided, use the current :ref:`Workspace options` to determine which :class:`~baboossh.Endpoint` to probe. If it is not set, try every endpoint in the :ref:`Scope`.

After completion, information will be added to endpoint list : endpoints will as `reachable` and their distance will be set.

