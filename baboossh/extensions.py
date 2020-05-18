import importlib
import inspect
import os

class Extensions():
    """Load and access available extensions"""

    auths = {}
    payloads = {}
    exports = {}
    imports = {}

    @classmethod
    def load(cls):
        """Load extensions from the dedicated folder

        Load extensions and sort them according to their type:
        * Authentication Methods
        * Payloads
        * Exporter
        * Importer
        """

        nb_ext = 0
        extensions_dir = os.path.join(os.path.dirname(__file__), 'ext_dir')
        files = [f.split('.')[0] for f in os.listdir(extensions_dir) if os.path.isfile(os.path.join(extensions_dir, f)) and f[0] != '.']
        for mod in files:
            module_name = "baboossh.ext_dir."+mod
            try:
                new_module = importlib.import_module(module_name)
            except Exception as exc:
                print("Couldn't load extension "+mod+" :"+str(exc))
                continue
            else:
                for name, data in inspect.getmembers(new_module):
                    if not inspect.isclass(data):
                        continue
                    if name != "BaboosshExt":
                        continue

                    module_type = data.getModType()
                    if module_type == "auth":
                        dico = cls.auths
                    elif module_type == "payload":
                        dico = cls.payloads
                    elif module_type == "export":
                        dico = cls.exports
                    elif module_type == "import":
                        dico = cls.imports
                    else:
                        print(mod+"> module type Invalid")
                        continue
                    if data.getKey() in dico.keys():
                        print(mod+"> "+module_type+' method "'+data.getKey()+'" already registered')
                        continue
                    dico[data.getKey()] = data
                    nb_ext = nb_ext+1
        print(str(nb_ext)+" extensions loaded.")
