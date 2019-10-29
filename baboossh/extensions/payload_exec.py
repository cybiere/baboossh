import asyncio, asyncssh

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):
    @classmethod
    def getModType(cls):
        return "payload"

    @classmethod
    def getKey(cls):
        return "exec"

    @classmethod
    def descr(cls):
        return "Exec command on target"

    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('cmd',nargs="+",help='Command to execute on target')

    @classmethod
    async def run(cls,conn, connection, wspaceFolder, stmt):
        command = " ".join(getattr(stmt,"cmd",["hostname"]))
        try:
            result = await conn.run(command)
            print(result.stdout,end='')
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
