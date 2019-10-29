import sqlite3
from baboossh.params import dbConn
import asyncio, asyncssh, sys
import multiprocessing as mp

async def listenAndLock(c,port,q):
    try:
        listener = await c.forward_socks('localhost',port)
    except Exception as e:
        q.put((False,str(e)))
        return
    q.put((True,"ok"))
    await listener.wait_closed()

def proxLock(c,port,q):
    asyncio.get_event_loop().run_until_complete(listenAndLock(c,port,q))

class Tunnel():
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
        self.subprocess = mp.Process(target=proxLock,args=(self.socket,self.port,q))
        self.subprocess.start()
        worked,msg = q.get()
        if not worked:
            raise ValueError(msg)
        print("Tunnel to "+str(self.connection)+" open on port "+str(self.port))

    def getPort(self):
        return self.port

    def close(self):
        self.subprocess.terminate()
        self.socket.close()
        print("Tunnel port "+str(self.port)+" closed")

    def __str__(self):
        return str(self.port)+"->"+str(self.connection)

