from os.path import join,exists
from os import mkdir
import sys
from baboossh.exceptions import ConnectionClosedError

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
    def run(cls, connection, wspaceFolder, stmt):
        if connection.conn is None:
            raise ConnectionClosedError

        lootFolder = join(wspaceFolder,"loot",str(connection.endpoint).replace(':','-'),"")
        if not exists(lootFolder):
            mkdir(lootFolder)
        filepath = getattr(stmt,'file',None)
        if filepath is None:
            print("You must specify a path")
            return False
        #TODO check if file or folder
        print("Retreiving file "+filepath+"... ",end="")
        sys.stdout.flush()
        filedest=join(lootFolder,filepath.replace('/','_'))
        try:
            connection.conn.get(filepath,filedest)
        except Exception as e:
            print("Error "+str(type(e))+": "+str(e))
            return False
        print("Done")
        print("File saved as "+filedest)

