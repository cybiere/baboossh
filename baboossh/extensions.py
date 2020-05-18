import importlib
import inspect
import threading
import os

class Extensions():
    """Load and access available extensions"""

    __auths = {}
    __payloads = {}
    __exports = {}
    __imports = {}

    @classmethod
    def load(cls):
        """Load extensions from the dedicated folder

        Load extensions and sort them according to their type:
        * Authentication Methods
        * Payloads
        * Exporter
        * Importer
        """

        nbExt = 0
        extensionsFolder = os.path.join(os.path.dirname(__file__), 'ext_dir')
        files = [f.split('.')[0] for f in os.listdir(extensionsFolder) if os.path.isfile(os.path.join(extensionsFolder, f)) and f[0] != '.']
        for mod in files:
            moduleName = "baboossh.ext_dir."+mod
            try:
                newMod = importlib.import_module(moduleName)
            except Exception as e:
                print("Couldn't load extension "+mod+" :"+str(e))
                continue
            else:
                for name, data in inspect.getmembers(newMod):
                    if not inspect.isclass(data):
                        continue
                    if name != "BaboosshExt":
                        continue
        
                    modType = data.getModType()
                    if modType == "auth":
                        dico = cls.__auths
                    elif modType == "payload":
                        dico = cls.__payloads
                    elif modType == "export":
                        dico = cls.__exports
                    elif modType == "import":
                        dico = cls.__imports
                    else:
                        print(mod+"> module type Invalid")
                        continue
                    if data.getKey() in dico.keys():
                        print(mod+"> "+modType+' method "'+data.getKey()+'" already registered')
                        continue
                    dico[data.getKey()] = data
                    nbExt = nbExt+1
        print(str(nbExt)+" extensions loaded.")

    @classmethod
    def getAuthMethod(cls, key):
        """Get an authentication method by its key

        Args:
            key (str): the desired method key

        Returns:
            The AuthMethod class
        """

        if key not in cls.__auths.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.__auths[key]

    @classmethod
    def authMethodsAvail(cls):
        """Get all available authentication methods

        Returns:
            A list of the keys of available methods
        """

        return cls.__auths.keys()

    @classmethod
    def getPayload(cls, key):
        """Get a payload by its key

        Args:
            key (str): the desired payload key

        Returns:
            The Payload class
        """

        if key not in cls.__payloads.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.__payloads[key]

    @classmethod
    def payloadsAvail(cls):
        """Get all available payloads

        Returns:
            A list of the keys of available payloads
        """

        return cls.__payloads.keys()

    @classmethod
    def getExport(cls, key):
        """Get an exporter by its key

        Args:
            key (str): the desired exporter key

        Returns:
            The Exporter class
        """

        if key not in cls.__exports.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.__exports[key]

    @classmethod
    def exportsAvail(cls):
        """Get all available exporters

        Returns:
            A list of the keys of exporters
        """

        return cls.__exports.keys()

    @classmethod
    def getImport(cls, key):
        """Get an importer by its key

        Args:
            key (str): the desired importer key

        Returns:
            The Importer class
        """

        if key not in cls.__imports.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.__imports[key]

    @classmethod
    def importsAvail(cls):
        """Get all available importers

        Returns:
            A list of the keys of available importers
        """

        return cls.__imports.keys()
