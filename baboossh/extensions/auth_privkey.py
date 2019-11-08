import json
import readline
from os.path import join,exists,basename
from os import remove
import sys
import subprocess
import cmd2
import asyncssh

class BaboosshExt():
    @classmethod
    def getModType(cls):
        return "auth"

    @classmethod
    def getKey(cls):
        return "privkey"

    @classmethod
    def descr(cls):
        return "Public/Private key authentication"

    @classmethod
    def checkKeyfile(cls,filepath):
        haspass = False
        valid = False
        try:
            with open(filepath,"r") as f:
                data = f.read()
            key = asyncssh.import_private_key(data)
        except asyncssh.public_key.KeyImportError as e:
            if "Passphrase must be specified to import" in str(e):
                valid = True
                haspass = True
        except:
            pass
        else:
            valid = True
        return valid,haspass

    @classmethod
    def checkPassphrase(cls,filepath,passphrase):
        try:
            with open(filepath,"r") as f:
                data = f.read()
            key = asyncssh.import_private_key(data,passphrase)
        except:
            pass
        else:
            return True
        return False

    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('file',help='Private key file path',completer_method=cmd2.Cmd.path_complete)
        parser.add_argument('passphrase',help='Private key passphrase',nargs="?")

    @classmethod
    def fromStatement(cls,stmt):
        passphrase = vars(stmt)['passphrase']
        if passphrase is None:
            passphrase = ""
        keypath = vars(stmt)['file']
        valid,haspass = cls.checkKeyfile(keypath)
        if not valid:
            raise ValueError(keypath+" isn't a valid key file")
        if haspass:
            passOk = cls.checkPassphrase(keypath,passphrase)
            if not passOk:
                print("Invalid passphrase, key saved without passphrase")
                passphrase = ""
        return json.dumps({'passphrase':passphrase,'keypath':keypath,'haspass':haspass})

    def __init__(self,creds):
        data = json.loads(creds)
        if "keypath" not in data.keys():
            raise ValueError
        self.keypath = data['keypath']
        if "haspass" in data.keys():
            if "passphrase" in data.keys():
                self.passphrase = data['passphrase']
            else:
                self.passphrase = ""
            self.haspass = data["haspass"]
        else:
            self.passphrase = ""
            self.haspass = False

    def serialize(self):
        ser = json.dumps({'passphrase':self.passphrase,'keypath':self.keypath,'haspass':self.haspass})
        return ser

    def getKwargs(self):
        if self.haspass:
            return {"client_keys":[self.keypath],"passphrase":self.passphrase}
        return {"client_keys":[self.keypath]}

    def getIdentifier(self):
        return self.keypath

    def toList(self):
        if self.haspass:
            if self.passphrase == "":
                return self.keypath+" > [?]"
            return self.keypath+" > "+self.passphrase
        return self.keypath

    def show(self):
        print("File path: "+self.keypath)
        print("Has passphrase? "+str(self.haspass))
        if self.haspass:
            if self.passphrase == "":
                print("Passphrase unknown")
            else:
                print("Passphrase: "+self.passphrase)

    def edit(self):
        if self.haspass:
            if self.passphrase == "":
                passphrase = input("Private key passphrase: ")
                if passphrase != "":
                    passOk = self.__class__.checkPassphrase(self.keypath,passphrase)
                    if not passOk:
                        print("Invalid passphrase, no changes saved")
                    else:
                        self.passphrase = passphrase
                        print("Passphrase valid, saving info.")
                else:
                    print("No changes saved")
            else:
                print("Working passphrase already defined")
        else:
            print("Private key doesn't have a passphrase")

    def delete(self):
        remove(self.keypath)
        return

