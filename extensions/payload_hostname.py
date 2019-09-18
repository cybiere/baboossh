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
        return "hostname"

    @classmethod
    def descr(cls):
        return "Print target hostname"

    @classmethod
    async def run(cls,conn, connection, wspaceFolder):
        try:
            result = await conn.run("hostname")
            print(result.stdout,end='')
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
