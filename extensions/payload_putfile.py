from os.path import basename
import sys
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
        return "putfile"

    @classmethod
    def descr(cls):
        return "Copy file to target"
    
    @classmethod
    async def run(cls,socket, connection, wspaceFolder):
        try:
            e = cls(socket,connection, wspaceFolder)
            await e.start()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True

    def __init__(self,socket,connection,wspaceFolder):
        self.socket = socket
        self.connection = connection
        self.wspaceFolder = wspaceFolder
    
    async def start(self):
        filepath = input('Local file% ')
        print("Pushing file "+filepath+"... ",end="")
        sys.stdout.flush()
        filename = basename(filepath)
        try:
            await asyncssh.scp(filepath,(self.socket,filename),recurse=True)
        except Exception as e:
            print("Error "+str(type(e))+": "+str(e))
            return False
        print("Done")
        print("File pushed as ~/"+filename)



