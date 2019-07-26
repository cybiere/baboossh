import json

class SpreadExt():
    @classmethod
    def getModType(cls):
        return "auth"

    @classmethod
    def getKey(cls):
        return "pubkey"

    @classmethod
    def descr(cls):
        return "Public/Private key authentication"

    @classmethod
    def build(cls):
        keypath = input("Path to private key file: ")
        if keypath == "":
            print("Key path cannot be empty")
            raise ValueError()
        passphrase = input("Private key passphrase (empty for none): ")
        return SpreadMod(json.dumps({'passphrase':passphrase,'keypath':keypath}))

    def __init__(self,creds):
        data = json.loads(creds)
        if "keypath" not in data.keys():
            raise ValueError
        self.keypath = data['keypath']
        if "passphrase" in data.keys():
            self.passphrase = data['passphrase']
        else:
            self.passphrase = ""

    def serialize(self):
        return json.dumps({'passphrase':self.passphrase,'keypath':self.keypath})

    def run(self):
        print("%%%%% Key authentication with "+self.keypath+" and passphrase "+self.passphrase)

