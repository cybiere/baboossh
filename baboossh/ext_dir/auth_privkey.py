import json
from os import remove, path
import cmd2
import paramiko

class BaboosshExt():
    _KEY_CLASSES = (paramiko.RSAKey, paramiko.ECDSAKey, paramiko.Ed25519Key)

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
        try:
            if path.getsize(filepath) == 0:
                print("Warning : empty file "+filepath+". Ignoring.")
                return False,False
        except OSError:
            print("Warning : could not open "+filepath+". Ignoring.")
            return False, False

        #Try loading the file with no password against each supported key type.
        #A PasswordRequiredException means the file is a valid (encrypted) key of some
        #type, even if we haven't pinned down which one yet - the exact type gets
        #resolved later once the real passphrase is known (see checkPassphrase/auth).
        for keyClass in cls._KEY_CLASSES:
            try:
                k = keyClass.from_private_key_file(filepath)
            except paramiko.ssh_exception.PasswordRequiredException:
                return True, True
            except paramiko.ssh_exception.SSHException:
                continue
            else:
                return True, False
        return False, False

    @classmethod
    def checkPassphrase(cls,filepath,passphrase):
        for keyClass in cls._KEY_CLASSES:
            try:
                k = keyClass.from_private_key_file(filepath,password=passphrase)
            except paramiko.ssh_exception.SSHException:
                continue
            else:
                return True
        return False

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

    def auth(self, username, transport):
        #TODO err handling
        if self.haspass:
            if self.passphrase == "":
                raise ValueError("Cannot use this privkey, passphrase is unknown")
            passphrase = self.passphrase
        else:
            passphrase = None

        key = None
        for keyClass in self._KEY_CLASSES:
            try:
                key = keyClass.from_private_key_file(self.keypath,password=passphrase)
            except paramiko.ssh_exception.SSHException:
                continue
            else:
                break

        if key is None:
            return False

        transport.auth_publickey(username, key)
        return True

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
