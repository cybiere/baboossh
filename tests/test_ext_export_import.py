from unittest.mock import MagicMock

from baboossh import Creds, Endpoint, Host, User
from baboossh.ext_dir.export_comprograph import BaboosshExt as ExportComprograph
from baboossh.ext_dir.import_nmapxml import BaboosshExt as ImportNmapxml

# import-textlist.py's module name has a hyphen, needs importlib
import importlib
ImportTextlist = importlib.import_module("baboossh.ext_dir.import-textlist").BaboosshExt


def make_stmt(**kwargs):
    stmt = MagicMock(spec=list(kwargs.keys()))
    for key, value in kwargs.items():
        setattr(stmt, key, value)
    return stmt


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def make_host(name="h1"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    return host


# --- export_comprograph ---

def test_export_getters():
    assert ExportComprograph.getModType() == "export"
    assert ExportComprograph.getKey() == "comprograph"


def test_export_extstr():
    assert str(ExportComprograph) == "comprograph"


def test_export_findings_true_branch(workspace, tmp_path):
    endpoint = make_endpoint()
    found_endpoint = Endpoint("5.6.7.8", "22")
    found_endpoint.found = endpoint
    found_endpoint.save()
    user = User("bob")
    user.found = endpoint
    user.save()
    creds = Creds("password", "hunter2")
    creds.found = endpoint
    creds.save()

    outfile = tmp_path / "graph.dot"
    stmt = make_stmt(output=str(outfile), findings=True)
    result = ExportComprograph.run(stmt, workspace)
    assert result is True
    content = outfile.read_text()
    assert "Findings" in content
    assert "Endpoints" in content
    assert "Users" in content
    assert "Creds" in content


def test_export_bug12_write_failure_returns_false(workspace, capsys):
    make_endpoint()
    stmt = make_stmt(output="/nonexistent/dir/graph.dot", findings=False)
    result = ExportComprograph.run(stmt, workspace)
    assert result is False
    assert "Error" in capsys.readouterr().out


# --- import_nmapxml ---

NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
<host>
<status state="up"/>
<address addr="10.0.0.9" addrtype="ipv4"/>
<ports>
<port protocol="tcp" portid="22">
<state state="open"/>
<service name="ssh"/>
</port>
</ports>
</host>
</nmaprun>
"""


def test_import_nmapxml_getters():
    assert ImportNmapxml.getModType() == "import"
    assert ImportNmapxml.getKey() == "nmap-xml"


def test_import_nmapxml_extstr():
    assert str(ImportNmapxml) == "nmap-xml"


def test_params_parser_from_rename_works_through_cmd2_convention(workspace):
    make_host("myhost")
    shell = MagicMock()
    result = ImportNmapxml.params_parser_from(shell)
    assert "myhost" in result
    assert "Local" in result


def test_import_nmapxml_local_source(workspace, tmp_path):
    xmlfile = tmp_path / "scan.xml"
    xmlfile.write_text(NMAP_XML)
    stmt = make_stmt(nmapfile=str(xmlfile), **{"from": "Local"})
    result = ImportNmapxml.run(stmt, workspace)
    assert result is True
    endpoint = Endpoint.find_one(ip_port="10.0.0.9:22")
    assert endpoint is not None
    assert endpoint.distance == 0


def test_import_nmapxml_no_source_skips_paths(workspace, tmp_path, capsys):
    xmlfile = tmp_path / "scan.xml"
    xmlfile.write_text(NMAP_XML)
    stmt = make_stmt(nmapfile=str(xmlfile), **{"from": None})
    result = ImportNmapxml.run(stmt, workspace)
    assert result is True
    assert "ignoring paths" in capsys.readouterr().out
    endpoint = Endpoint.find_one(ip_port="10.0.0.9:22")
    assert endpoint is not None
    assert endpoint.distance is None


def test_import_nmapxml_unknown_host_returns_false(workspace, tmp_path, capsys):
    xmlfile = tmp_path / "scan.xml"
    xmlfile.write_text(NMAP_XML)
    stmt = make_stmt(nmapfile=str(xmlfile), **{"from": "nosuchhost"})
    result = ImportNmapxml.run(stmt, workspace)
    assert result is False
    assert "No host corresponding" in capsys.readouterr().out


def test_import_nmapxml_bug10_unprobed_host_returns_false(workspace, tmp_path, capsys):
    host = make_host("unprobed")
    endpoint = make_endpoint("9.9.9.9", "22")
    endpoint.host = host
    endpoint.save()
    xmlfile = tmp_path / "scan.xml"
    xmlfile.write_text(NMAP_XML)
    stmt = make_stmt(nmapfile=str(xmlfile), **{"from": "unprobed"})
    result = ImportNmapxml.run(stmt, workspace)
    assert result is False
    assert "has not been probed yet" in capsys.readouterr().out


def test_import_nmapxml_bad_file_returns_false(workspace, tmp_path, capsys):
    xmlfile = tmp_path / "bad.xml"
    xmlfile.write_text("not xml at all")
    stmt = make_stmt(nmapfile=str(xmlfile), **{"from": "Local"})
    result = ImportNmapxml.run(stmt, workspace)
    assert result is False
    assert "Failed to read source file" in capsys.readouterr().out


# --- import-textlist ---

def test_textlist_getters():
    assert ImportTextlist.getModType() == "import"
    assert ImportTextlist.getKey() == "textlist"


def test_textlist_extstr():
    assert str(ImportTextlist) == "textlist"


def test_textlist_bug9_invalid_object_type_message(workspace, capsys):
    stmt = make_stmt(object_type="invalid", userfile="/tmp/whatever")
    result = ImportTextlist.run(stmt, workspace)
    assert result is False
    assert "Invalid object type: invalid" in capsys.readouterr().out


def test_textlist_user_branch(workspace, tmp_path):
    userfile = tmp_path / "users.txt"
    userfile.write_text("alice\nbob\n")
    stmt = make_stmt(object_type="user", userfile=str(userfile))
    result = ImportTextlist.run(stmt, workspace)
    assert result is True
    assert User.find_one(name="alice") is not None
    assert User.find_one(name="bob") is not None


def test_textlist_password_branch(workspace, tmp_path):
    passfile = tmp_path / "passwords.txt"
    passfile.write_text("hunter2\nswordfish\n")
    stmt = make_stmt(object_type="password", userfile=str(passfile))
    result = ImportTextlist.run(stmt, workspace)
    assert result is True
    creds = Creds.find_all()
    contents = [c.obj.creds for c in creds]
    assert "hunter2" in contents
    assert "swordfish" in contents


def test_textlist_endpoint_branch_with_malformed_line(workspace, tmp_path, capsys):
    endpointfile = tmp_path / "endpoints.txt"
    endpointfile.write_text("10.0.0.5\nnot-a-valid-ip\n10.0.0.6\n")
    stmt = make_stmt(object_type="endpoint", userfile=str(endpointfile))
    result = ImportTextlist.run(stmt, workspace)
    assert result is True
    out = capsys.readouterr().out
    assert "could not parse line" in out
    assert Endpoint.find_one(ip_port="10.0.0.5:22") is not None
    assert Endpoint.find_one(ip_port="10.0.0.6:22") is not None
    assert "2 endpoint(s) read" in out


def test_textlist_missing_file_returns_false(workspace, capsys):
    stmt = make_stmt(object_type="user", userfile="/nonexistent/file.txt")
    result = ImportTextlist.run(stmt, workspace)
    assert result is False
    assert "Failed to read source file" in capsys.readouterr().out
