import asyncio, asyncssh
from src.host import Host

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):
    @classmethod
    def getModType(cls):
        return "payload"

    @classmethod
    def getKey(cls):
        return "identify"

    @classmethod
    def descr(cls):
        return "Generate a host identifier for the connection"
    
    @classmethod
    def buildParser(cls,parser):
        pass

    @classmethod
    async def run(cls,socket, connection,wspaceFolder, stmt):
        try:
            print("## HOSTNAME ##")
            result = await socket.run("hostname")
            hostname = result.stdout.rstrip()
            print(hostname)
            print("## UNAME ##")
            result = await socket.run("uname -a")
            uname = result.stdout.rstrip()
            print(uname)
            print("## ISSUE ##")
            result = await socket.run("cat /etc/issue")
            issue = result.stdout.rstrip()
            print(issue)
            print("## MACHINE-ID ##")
            result = await socket.run("cat /etc/machine-id")
            machineId = result.stdout.rstrip()
            print(machineId)
            print("## MAC addresses ##")
            result = await socket.run("for i in `ls -l /sys/class/net/ | grep -v virtual | grep 'devices' | tr -s '[:blank:]' | cut -d ' ' -f 9 | sort`; do ip l show $i | grep ether | tr -s '[:blank:]' | cut -d ' ' -f 3; done")
            macStr = result.stdout.rstrip()
            macs = macStr.split()
            print("## DONE ##")
            newHost = Host(hostname,uname,issue,machineId,macs)
            if newHost.getId() is None:
                print("New host")
            else:
                print("Existing host")
            newHost.save()
            e = connection.getEndpoint()
            e.setHost(newHost)
            e.save()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
