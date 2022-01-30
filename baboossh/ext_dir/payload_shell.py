from baboossh.exceptions import ConnectionClosedError
from paramiko.py3compat import u
import select
import termios
import tty
import sys



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
    def buildParser(cls,parser):
        pass

    @classmethod
    def run(cls, connection,wspaceFolder, stmt):
        if connection.transport is None:
            raise ConnectionClosedError

        #TODO : error handling
        chan = connection.transport.open_channel("session",timeout=3)
        chan.get_pty()
        chan.invoke_shell()
        
        oldtty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            chan.settimeout(0.0)
        
            while True:
                r, w, e = select.select([chan, sys.stdin], [], [])
                if chan in r:
                    try:
                        x = u(chan.recv(1024))
                        if len(x) == 0:
                            sys.stdout.write("\r\n*** EOF\r\n")
                            break
                        sys.stdout.write(x)
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                if sys.stdin in r:
                    x = sys.stdin.read(1)
                    if len(x) == 0:
                        break
                    chan.send(x)
        
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

        chan.close()
        return True
    
