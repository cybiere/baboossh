import json
import readline
from os.path import join,exists,basename
import subprocess
from Cryptodome.PublicKey import RSA, DSA, ECC

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
    def listContent(cls,folder):
        ret = []
        res = subprocess.run(["ls","-FA",folder], stdout=subprocess.PIPE)
        for element in res.stdout.decode('utf-8').splitlines():
            ret.append(join(folder,element))
        return ret

    @classmethod
    def complete(cls, text, state):
        response = None
        if state == 0:
            if text == "":
                folder = "/"
            else:
                path,sep,t = text.rpartition("/")
                if path == "":
                    folder = "/"
                else:
                    folder = path+"/"
            cls.options = cls.listContent(folder)
            # This is the first time for this text, so build a match list.
            if text:
                cls.matches = [s 
                                for s in cls.options
                                if s and s.startswith(text)]
            else:
                cls.matches = cls.options[:]
        try:
            response = cls.matches[state]
        except IndexError:
            response = None
        return response

    @classmethod
    def checkKeyfile(cls,filepath):
        haspass = False
        valid = True
        try:
            key = RSA.import_key(open(filepath).read())
        except UnicodeDecodeError:
            valid = False
        except ValueError as e:
            if "PEM is encrypted" in str(e):
                haspass = True
            else:
                try:
                    key = DSA.import_key(open(filepath).read())
                except ValueError as e:
                    try:
                        key = ECC.import_key(open(filepath).read())
                    except ValueError as e:
                        valid = False
                    except:
                        raise
        return valid,haspass

    @classmethod
    def checkPassphrase(cls,filepath,passphrase):
        for keyType in [RSA,DSA,ECC]:
            try:
                key = keyType.import_key(open(filepath).read(),passphrase=passphrase)
            except:
                pass
            else:
                return True
        return False

    @classmethod
    def build(cls):
        oldcompleter = readline.get_completer()
        readline.set_completer(cls.complete)
        keypath = input("Path to private key file: ")
        readline.set_completer(oldcompleter)
        if keypath == "":
            raise ValueError("Key path cannot be empty")
        valid,haspass = cls.checkKeyfile(keypath)
        if not valid:
            raise ValueError(keypath+" isn't a valid key file")
        if haspass:
            passphrase = input("Private key passphrase (empty if unknown): ")
            if passphrase != "":
                passOk = cls.checkPassphrase(keypath,passphrase)
                if not passOk:
                    raise ValueError("Invalid passphrase, please retry")
        else:
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
            return {"key_filename":self.keypath,"passphrase":self.passphrase}
        return {"key_filename":self.keypath}

    def getIdentifier(self):
        return self.keypath

    def toList(self):
        if self.haspass:
            if self.passphrase == "":
                return self.keypath+" [?]"
            return self.keypath+" [✔]"
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


