from os.path import join,exists
from os import mkdir
import sys
from baboossh.exceptions import ConnectionClosedError
from paramiko import SFTPClient

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
        if connection.transport is None:
            raise ConnectionClosedError

        lootFolder = join(wspaceFolder,"loot",str(connection.endpoint).replace(':','-'),"")
        if not exists(lootFolder):
            mkdir(lootFolder)
        filepath = getattr(stmt,'file',None)
        if filepath is None:
            print("You must specify a path")
            return False

        filedest=join(lootFolder,filepath.replace('/','_'))
        
        #TODO err management
        sftp = SFTPClient.from_transport(connection.transport)
        print("Retreiving file "+filepath+"... ",end="")
        sys.stdout.flush()
        try:
            sftp.get(filepath,filedest)
        except Exception as e:
            print("Error "+str(type(e))+": "+str(e))
            return False
        print("Done")
        print("File saved as "+filedest)

        #sftp.put(localpath,filepath)

