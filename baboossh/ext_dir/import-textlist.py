import cmd2
from baboossh import User, Creds, Endpoint

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):
    @classmethod
    def getModType(cls):
        return "import"

    @classmethod
    def getKey(cls):
        return "textlist"

    @classmethod
    def descr(cls):
        return "Import users a text file (one username per line)"

    @classmethod
    def buildParser(cls,parser):
        object_types = ['user', 'password', 'endpoint']
        parser.add_argument('object_type',help='Object to import',choices=object_types)
        parser.add_argument('userfile',help='User list file path',completer=cmd2.Cmd.path_complete)

    @classmethod
    def run(cls,stmt,workspace):
        object_type = getattr(stmt,'object_type')
        userfile = getattr(stmt,'userfile')
        
        if object_type not in ['user', 'password', 'endpoint']:
            print("Invalid object type: "+str(e))
            return False

        try:
            with open(userfile) as f:
                lines = f.read().splitlines()
        except Exception as e:
            print("Failed to read source file: "+str(e))
            return False

        count = 0
        count_new = 0

        for line in lines:
            count = count + 1   
            if object_type == "user":
                new_user = User(line)
                if new_user.id is None:
                    count_new = count_new + 1
                new_user.save()
            if object_type == "password":
                new_cred = Creds("password",line)
                if new_cred.id is None:
                    count_new = count_new + 1
                new_cred.save()
            if object_type == "endpoint":
                try:
                    new_endpoint = Endpoint(line,"22")
                except Exception as e:
                    print("Warning : could not parse line \""+line+"\" as a valid endpoint address. Ignored")
                    count = count - 1
                    continue
                if new_endpoint.id is None:
                    count_new = count_new + 1
                new_endpoint.save()

        print(str(count)+" "+object_type+"(s) read, "+str(count_new)+" new "+object_type+"(s) saved")
        return True
            


 
