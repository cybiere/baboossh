from os.path import join,exists,basename
from os import mkdir
import readline
import sys
import subprocess

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
        res = subprocess.run(["ls","-FA",folder], stdout=subprocess.PIPE)
        for element in res.stdout.decode('utf-8').splitlines():
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
        oldcompleter = readline.get_completer()
        readline.set_completer(self.complete)
        filepath = input('Local file% ')
        readline.set_completer(oldcompleter)
        print("Pushing file "+filepath+"... ",end="")
        sys.stdout.flush()
        filename = basename(filepath)
        #TODO check if file or folder
        self.socket.put(filepath,filename)
        print("Done")
        print("File pushed as ~/"+filename)



