class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):
    @classmethod
    def getModType(cls):
        return "payload"

    @classmethod
    def getKey(cls):
        return "shell"

    @classmethod
    def descr(cls):
        return "Get a shell on target"
    
    @classmethod
    def run(cls,socket, connection,wspaceFolder):
        try:
            socket.run("sh",pty=True)
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
