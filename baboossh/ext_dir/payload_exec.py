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
        return "exec"

    @classmethod
    def descr(cls):
        return "Exec command on target"

    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('cmd',nargs="+",help='Command to execute on target')

    @classmethod
    def run(cls, connection, wspaceFolder, stmt):
        if connection.transport is None:
            raise ConnectionClosedError
        command = " ".join(getattr(stmt,"cmd",["hostname"]))
        try:
            output = connection.exec_command(command)
            print(output)
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
