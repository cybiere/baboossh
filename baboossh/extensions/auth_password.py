class BaboosshExt():
    @classmethod
    def getModType(cls):
        return "auth"

    @classmethod
    def getKey(cls):
        return "password"

    @classmethod
    def descr(cls):
        return "Password authentication"

    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('value',help='Password value')

    @classmethod
    def fromStatement(cls,stmt):
        return vars(stmt)['value']

    def __init__(self,creds):
        self.creds = creds

    def serialize(self):
        return self.creds

    def getKwargs(self):
        return {"password":self.creds,"client_keys":None}

    def getIdentifier(self):
        return self.creds

    def toList(self):
        return self.creds

    def show(self):
        print("Password: "+self.creds)

    def edit(self):
        print("Nothing to edit")
    
    def delete(self):
        return
