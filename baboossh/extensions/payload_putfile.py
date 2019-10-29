from os.path import basename
import sys,cmd2
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
    def buildParser(cls,parser):
        parser.add_argument('file',help='Path of file to send to target',completer_method=cmd2.Cmd.path_complete)

    @classmethod
    async def run(cls,socket, connection, wspaceFolder, stmt):
        try:
            e = cls(socket,connection, wspaceFolder, stmt)
            await e.start()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True

    def __init__(self,socket,connection,wspaceFolder,stmt):
        self.socket = socket
        self.connection = connection
        self.wspaceFolder = wspaceFolder
        self.stmt = stmt
    
    async def start(self):
        filepath = getattr(self.stmt,'file',None)
        if filepath is None:
            print("You must specify a path")
            return False
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



