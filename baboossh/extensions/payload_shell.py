import asyncio, asyncssh, sys
from os import dup

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class MySSHClientSession(asyncssh.SSHClientSession):
    def data_received(self, data, datatype):
        print(data, end='')
    def connection_lost(self, exc):
        if exc:
            print('SSH session error: ' + str(exc), file=sys.stderr)

class BaboosshExt(object,metaclass=ExtStr):
    @classmethod
    def getModType(cls):
        return "payload"

    @classmethod
    def getKey(cls):
        return "shell"

    @classmethod
    def descr(cls):
        return "Get a shell on target"
    
    @classmethod
    def buildParser(cls,parser):
        pass

    @classmethod
    async def run(cls,socket, connection,wspaceFolder, stmt):
        try:
            sout = dup(sys.stdout.fileno())
            sin = dup(sys.stdin.fileno())
            result = await socket.run(term_type="xterm", stdin=sin, stdout=sout, stderr=sout)
        except OSError as e:
            print(e.errno)
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
