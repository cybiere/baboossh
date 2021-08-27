import cmd2
from libnmap.parser import NmapParser, NmapParserException
from baboossh.host import Host
from baboossh.endpoint import Endpoint
from baboossh.path import Path

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):
    @classmethod
    def getModType(cls):
        return "import"

    @classmethod
    def getKey(cls):
        return "nmap-xml"

    @classmethod
    def descr(cls):
        return "Import endpoints from NMAP XML output file"

    def params_parser_from(self):
        all_hosts = Host.find_all()
        ret = []
        for host in all_hosts:
            ret.append(host.name)
        ret.append("Local")
        return ret

    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('nmapfile',help='NMAP file path',completer=cmd2.Cmd.path_complete)
        parser.add_argument('from',help='Host from which scan was performed',nargs='?',choices_provider=cls.params_parser_from)

    @classmethod
    def run(cls,stmt,workspace):
        nmapfile = getattr(stmt,'nmapfile')
        from_host = getattr(stmt,'from',"Local")

        if from_host is None:
            print("No source host specified, ignoring paths")
            distance = None
        elif from_host == "Local":
            src = None
            distance = 0
        else:
            host = Host.find_one(name=from_host)
            if host is None:
                print("No host corresponding.")
                return False
            src = host
            distance = src.distance + 1
        try:
            report = NmapParser.parse_fromfile(nmapfile)
        except Exception as e:
            print("Failed to read source file: "+str(e))
            return False
        count = 0
        count_new = 0
        for host in report.hosts:
            for s in host.services:
                if s.service == "ssh" and s.open():
                    count = count + 1
                    new_endpoint = Endpoint(host.address,s.port)
                    if new_endpoint.id is None:
                        count_new = count_new + 1
                    new_endpoint.save()
                    if distance is not None:
                        if new_endpoint.distance is None or new_endpoint.distance > distance:
                            new_endpoint.distance = distance
                            new_endpoint.save()
                        new_path = Path(src,new_endpoint)
                        new_path.save()
        print(str(count)+" endpoints found, "+str(count_new)+" new endpoints saved")
        return True
 
