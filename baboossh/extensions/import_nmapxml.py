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

    def testmeth(self):
        allHosts = Host.findAllNames()
        return allHosts + ['Local']

    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('nmapfile',help='NMAP file path',completer_method=cmd2.Cmd.path_complete)
        parser.add_argument('from',help='Host from which scan was performed',nargs='?',choices_method=cls.testmeth)

    @classmethod
    def run(cls,stmt,workspace):
        nmapfile = getattr(stmt,'nmapfile')
        fromHost = getattr(stmt,'from',"Local")

        if fromHost is None:
            src = None
            print("No source host specified, using Local")
        elif fromHost == "Local":
            src = None
        else:
            hosts = Host.findByName(fromHost)
            if len(hosts) > 1:
                print("Several hosts corresponding.")
                return False
            elif len(hosts) == 0:
                print("No host corresponding.")
                return False
            src = hosts[0]
        try:
            report = NmapParser.parse_fromfile(nmapfile)
        except Exception as e:
            print("Failed to read source file: "+str(e))
            return False
        count = 0
        countNew = 0
        for host in report.hosts:
            for s in host.services:
                if s.service == "ssh":
                    count = count + 1
                    newEndpoint = Endpoint(host.address,s.port)
                    if newEndpoint.getId() is None:
                        countNew = countNew + 1
                    newEndpoint.save()
                    newPath = Path(src,newEndpoint)
                    newPath.save()
        print(str(count)+" endpoints found, "+str(countNew)+" new endpoints saved")
        return True
 
