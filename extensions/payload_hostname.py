class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):
    @classmethod
    def getModType(cls):
        return "payload"

    @classmethod
    def getKey(cls):
        return "hostname"

    @classmethod
    def descr(cls):
        return "Print target hostname"
    
    @classmethod
    def run(cls,connection):
        try:
            connection.run("hostname")
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True
    
