from baboossh.exceptions import ConnectionClosedError
from paramiko.py3compat import u
from paramiko import SSHException
import socket



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
        return "Execute a command on target"
    
    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('cmd',nargs="+",help='Command to execute on target')

    @classmethod
    def run(cls, connection,wspaceFolder, stmt):
        if connection.transport is None:
            raise ConnectionClosedError
        command = " ".join(getattr(stmt,"cmd",["hostname"]))

        chan = connection.transport.open_channel("session",timeout=3)
        try:
            chan.exec_command(command)
            try:
                x = u(chan.recv(1024))
                while len(x) != 0:
                    print(x,end="")
                    x = u(chan.recv(1024))
            except socket.timeout:
                pass
            print("\r\n*** EOF\r\n")
        except SSHException:
            print("Error : exec command did not work, please try shell payload instead.");
            chan.close()
            return False

        chan.close()
        return True
    
