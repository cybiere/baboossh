import cmd2

class ExtStr(type):
    def __str__(self):
        return self.getKey()

class BaboosshExt(object,metaclass=ExtStr):
    @classmethod
    def getModType(cls):
        return "export"

    @classmethod
    def getKey(cls):
        return "comprograph"

    @classmethod
    def descr(cls):
        return "Export compromission graph as a dot file"

    @classmethod
    def buildParser(cls,parser):
        parser.add_argument('output',help='Output file path',completer_method=cmd2.Cmd.path_complete)

    @classmethod
    def run(cls,stmt,workspace):
        outfile = getattr(stmt,'output')
        dotcode = 'digraph compromission_graph {\nnode [shape=box];\nrankdir="LR";\n'
        for path in workspace.getPaths():
            src = path.getSrc()
            if src is None:
                src="local"
            dotcode = dotcode + '"'+str(src)+'" -> "'+str(path.getDst())+'"\n'
        dotcode = dotcode + '}'
        with open(outfile,"w") as f:
            f.write(dotcode)
        print("Export saved as "+outfile)
        return True
    
