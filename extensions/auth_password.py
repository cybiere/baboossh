
class SpreadExt():
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
    def build(cls):
        password = input("Password: ")
        if password == "":
            print("Password cannot be empty")
            raise ValueError()
        return cls(password)

    def __init__(self,creds):
        self.creds = creds

    def serialize(self):
        return self.creds

    def run(self):
        print("##### Password authentication with "+self.creds)

    def toList(self):
        return self.creds
