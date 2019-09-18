import asyncio, asyncssh, sys

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
    async def run(cls,socket, connection,wspaceFolder):
        try:
            result = await socket.create_process(term_type="xterm", stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
            await result.wait_closed()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
