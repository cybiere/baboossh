class SpreadExt():
    @classmethod
    def getModType(cls):
        return "payload"

    @classmethod
    def getKey(cls):
        return "hostname"

    @classmethod
    def descr(cls):
        return "Print target hostname"

    def run(self):
        print("#TODO")

