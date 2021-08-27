import json
from os import remove
import cmd2
import paramiko

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

        #Check haspass
        try:
           k = paramiko.RSAKey.from_private_key_file(filepath)
        except  paramiko.ssh_exception.PasswordRequiredException:
            haspass = True
        except:
            pass
        else:
            #RSA, no pass
            return True,False

        #random string to check the exception raised
        randpass = "cy2fFwHriD" if haspass else None
        try:
           k = paramiko.RSAKey.from_private_key_file(filepath,password=randpass)
        except paramiko.ssh_exception.SSHException as e:
            if "encountered" not in str(e) and "not a valid" not in str(e):
                return True, True
            try:
                k = paramiko.DSSKey.from_private_key_file(filepath,password=randpass)
            except paramiko.ssh_exception.SSHException as e:
                if "encountered" not in str(e) and "not a valid" not in str(e):
                    return True, True
                try:
                    k = paramiko.ECDSAKey.from_private_key_file(filepath,password=randpass)
                except paramiko.ssh_exception.SSHException as e:
                    if "encountered" not in str(e) and "not a valid" not in str(e):
                        return True, True
                    return False, False
                return True, haspass
            return True, haspass
        return True,haspass

    @classmethod
    def checkPassphrase(cls,filepath,passphrase):
        try:
           k = paramiko.RSAKey.from_private_key_file(filepath,password=passphrase)
        except paramiko.ssh_exception.SSHException as e: 
            try:
                k = paramiko.DSSKey.from_private_key_file(filepath,password=passphrase)
            except paramiko.ssh_exception.SSHException as e:
                try:
                    k = paramiko.ECDSAKey.from_private_key_file(filepath,password=passphrase)
                except paramiko.ssh_exception.SSHException as e:
                    return False
                return True
            return True
        return True

    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('file',help='Private key file path',completer=cmd2.Cmd.path_complete)
        parser.add_argument('passphrase',help='Private key passphrase',nargs="?")

    @classmethod
    def fromStatement(cls,stmt):
        passphrase = vars(stmt)['passphrase']
        if passphrase is None:
            passphrase = "cy2fFwHriD"
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
            if self.passphrase == "":
                raise ValueError("Cannot use this privkey, passphrase is unknown")
            return {"key_filename":self.keypath,"passphrase":self.passphrase}
        return {"key_filename":[self.keypath]}
    
    @property
    def identifier(self):
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
        #TODO flag for key file removal ?
        #remove(self.keypath)
        return

