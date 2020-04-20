import sqlite3
from baboossh.params import dbConn
import asyncio, asyncssh, sys
import multiprocessing as mp

class Tunnel():
    """Open SOCKS tunnel to a host to proxify other tools

    Each tunnel is opened in another process so that BabooSSH is still usable
    while the tunnel is open.

    Attributes:
        connection (:class:`.Connection`): the tunnel exit
        port (int): the tunnel entrance (local) port. Uses a random port if
            none is provided.
        socket (asyncssh.SSHClientConnection): the connection to the exit once
            it is opened.
    """

    async def listenAndLock(c,port,q):
        """Open the proxy on the connection and wait.

        Once the connection is opened, this function opens the proxy and waits.
        The success is returned to the main process as a boolean through a Queue,
        with the error message in case of failure.

        Args:
            c (asyncssh.SSHClientConnection): the opened connection to the exit
            port (int): the local entrance port
            q (multiprocessing.Queue): the queue to report status to the main process
        """

        try:
            listener = await c.forward_socks('localhost',port)
        except Exception as e:
            q.put((False,str(e)))
            return
        q.put((True,"ok"))
        await listener.wait_closed()

    def proxLock(c,port,q):
        """Run :func:`~tunnel.Tunnel.listenAndLock`

        Args:
            See :func:`~tunnel.Tunnel.listenAndLock`
        """

        asyncio.get_event_loop().run_until_complete(Tunnel.listenAndLock(c,port,q))

    def __init__(self,connection,port=None):
        self.connection = connection
        if port is None:
            from socket import socket, AF_INET, SOCK_STREAM
            s = socket(AF_INET, SOCK_STREAM)
            s.bind(('localhost', 0))
            addr, port = s.getsockname()
            s.close()
        self.port = port
        self.socket = self.connection.connect()
        q = mp.Queue()
        self.subprocess = mp.Process(target=Tunnel.proxLock,args=(self.socket,self.port,q))
        self.subprocess.start()
        worked,msg = q.get()
        if not worked:
            raise ValueError(msg)
        print("Tunnel to "+str(self.connection)+" open on port "+str(self.port))

    def getPort(self):
        """Get the tunnel port

        Returns:
            The tunnel entrance port (int)
        """

        return self.port

    def close(self):
        """Close a previously opened port"""
        self.subprocess.terminate()
        self.socket.close()
        print("Tunnel port "+str(self.port)+" closed")

    def __str__(self):
        return str(self.port)+"->"+str(self.connection)
