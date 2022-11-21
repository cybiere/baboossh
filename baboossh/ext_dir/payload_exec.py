from baboossh.exceptions import ConnectionClosedError
import select

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
            chan = connection.transport.open_session()
            chan.get_pty()
            chan.exec_command(command)
            output = ""
            while True:
                if chan.exit_status_ready():
                    output = output+chan.recv(1024).decode("utf-8")
                    break
                rl, wl, xl = select.select([chan], [], [], 0.0)
                if len(rl) > 0:
                    output = output+chan.recv(1024).decode("utf-8")
            print(output)
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
