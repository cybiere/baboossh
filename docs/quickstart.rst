Quick start
===========

After installing BabooSSH, you can start it simply by running `baboossh` in a terminal. At its first launch it will create the `.baboossh` folder in your home directory and the default :class:`~baboossh.Workspace`.

The first thing to do is to add an :class:`~baboossh.Endpoint`, using either the :ref:`endpoint command` or one of the :ref:`Importer extensions`::

   endpoint add 10.0.1.101 22

Then :ref:`probe <probe command>` the :class:`~baboossh.Endpoint` you just added to ensure it's SSH service can be reached from your position in the network::

   probe 10.0.1.101:22

You can then add a user and creds with :ref:`user <user command>` and :ref:`creds command`::

   user add sga
   creds add password 123456

Once the user, creds and endpoint are added and the endpoint has been probed, you can connect it to test if the user and creds allow you to authenticate on the endpoint::

   set user sga
   set creds #1
   set endpoint 10.0.1.101:22
   connect

If the connection is successful, BabooSSH will :func:`~baboossh.Connection.identify` the server in order to create a :class:`~baboossh.Host`.

You can list the successful connections with the :ref:`connection command`, and of course the hosts with the :ref:`host command`.

Once you have a valid connection, you can run :ref:`Payloads` on them. For instance, you can get an interactive shell on the target::

   run sga:#1@10.0.1.101:22 shell

You can also use the build-in :ref:`Gather payload` to fetch informations on the target concerning other users, creds and endpoints, which will be automatically added to the :class:`~baboossh.Workspace`::

   set payload gather
   run

Depending on found information, you will now have new targets. Some on these targets might not be reachable directly from your computer, but only from the compromised host. This is when you will need :ref:`Pivoting`. BabooSSH helps you to do that easily, using the :ref:`probe command`::

   probe 10.0.2.106:22

The pivot has been detected automatically, and when listing the :class:`~baboossh.Endpoint`, you can see the new endpoint has a distance of 2, which means it takes one pivot from your computer to reach it::

   endpoint list

You can then :ref:`set <set command>` this new endpoint as a target, and set the creds as `None` so that any :class:`~baboossh.Creds` in the current :class:`~baboossh.Workspace` will be sequentially tested until a working :class:`~baboossh.Connection` is found (or each creds object is tested)::

   set endpoint 10.0.2.106:22
   set creds
   connect

And once a working connection is obtained... Well, rinse and repeat !
