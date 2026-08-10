import importlib
import inspect
import os

from baboossh.ext_base import BaboosshAuthBase, BaboosshExtBase, BaboosshImportExportBase, BaboosshPayloadBase

__all__ = ["Extensions"]

class Extensions():
    """Load and access available extensions"""

    auths: dict[str, type[BaboosshAuthBase]] = {}
    payloads: dict[str, type[BaboosshPayloadBase]] = {}
    exports: dict[str, type[BaboosshImportExportBase]] = {}
    imports: dict[str, type[BaboosshImportExportBase]] = {}

    @classmethod
    def load(cls) -> None:
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
                    if not issubclass(data, BaboosshExtBase):
                        print(mod+"> BaboosshExt doesn't implement BaboosshExtBase")
                        continue

                    module_type = data.getModType()
                    if module_type not in ("auth", "payload", "export", "import"):
                        print(mod+"> module type Invalid")
                        continue

                    if module_type == "auth":
                        if not issubclass(data, BaboosshAuthBase):
                            print(mod+"> auth module doesn't implement BaboosshAuthBase")
                            continue
                        if data.getKey() in cls.auths.keys():
                            print(mod+"> "+module_type+' method "'+data.getKey()+'" already registered')
                            continue
                        cls.auths[data.getKey()] = data
                    elif module_type == "payload":
                        if not issubclass(data, BaboosshPayloadBase):
                            print(mod+"> payload module doesn't implement BaboosshPayloadBase")
                            continue
                        if data.getKey() in cls.payloads.keys():
                            print(mod+"> "+module_type+' method "'+data.getKey()+'" already registered')
                            continue
                        cls.payloads[data.getKey()] = data
                    elif module_type == "export":
                        if not issubclass(data, BaboosshImportExportBase):
                            print(mod+"> export module doesn't implement BaboosshImportExportBase")
                            continue
                        if data.getKey() in cls.exports.keys():
                            print(mod+"> "+module_type+' method "'+data.getKey()+'" already registered')
                            continue
                        cls.exports[data.getKey()] = data
                    else:
                        if not issubclass(data, BaboosshImportExportBase):
                            print(mod+"> import module doesn't implement BaboosshImportExportBase")
                            continue
                        if data.getKey() in cls.imports.keys():
                            print(mod+"> "+module_type+' method "'+data.getKey()+'" already registered')
                            continue
                        cls.imports[data.getKey()] = data
                    nb_ext = nb_ext+1
        print(str(nb_ext)+" extensions loaded.")
