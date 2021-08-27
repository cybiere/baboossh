from os.path import basename
import sys,cmd2
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
        return "putfile"

    @classmethod
    def descr(cls):
        return "Copy file to target"
    
    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('file',help='Path of file to send to target',completer=cmd2.Cmd.path_complete)

    @classmethod
    def run(cls, connection, wspaceFolder, stmt):
        if connection.conn is None:
            raise ConnectionClosedError

        filepath = getattr(stmt,'file',None)
        if filepath is None:
            print("You must specify a path")
            return False
        print("Pushing file "+filepath+"... ",end="")
        sys.stdout.flush()
        filename = basename(filepath)
        try:
            connection.conn.put(filepath,filename)
        except Exception as e:
            print("Error "+str(type(e))+": "+str(e))
            return False
        print("Done")
        print("File pushed as ~/"+filename)



