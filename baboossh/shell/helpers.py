"""Shared cmd2 completion providers and command categories for the Shell commands.

Every ``choices_provider`` used by the various command sections lives here as a
plain function taking the ``Shell`` instance explicitly (cmd2 supports this
calling convention natively, passing the app instance as the first positional
argument) so any section can reference any getter uniformly, regardless of
how many sections use it.
"""

import os
import cmd2
from baboossh.utils import WORKSPACES_DIR
from baboossh.extensions import Extensions

CMD_CAT_OBJ = "Object management"
CMD_CAT_CON = "Connecting hosts"
CMD_CAT_WSP = "Workspace management"


def get_option_creds(shell):
    return [cmd2.CompletionItem("#"+str(creds.id), creds.obj.toList()) for creds in shell.workspace.get_objects(creds=True, scope=True)]

def get_option_host(shell):
    return [cmd2.CompletionItem(str(host.name), "; ".join(str(e) for e in host.endpoints)) for host in shell.workspace.get_objects(hosts=True, scope=True)]

def get_arg_workspaces(shell):
    return [name for name in os.listdir(WORKSPACES_DIR) if os.path.isdir(os.path.join(WORKSPACES_DIR, name))]

def get_option_gateway(shell):
    return get_host_or_local(shell)

def get_option_user(shell):
    return [cmd2.CompletionItem(str(user), str(user)) for user in shell.workspace.get_objects(users=True, scope=True)]

def get_option_endpoint(shell):
    return [cmd2.CompletionItem(str(endpoint), "" if endpoint.host == None else str(endpoint.host)) for endpoint in shell.workspace.get_objects(endpoints=True, scope=True)]

def get_option_endpoint_tag(shell):
    endpoints = [cmd2.CompletionItem(str(endpoint), "" if endpoint.host == None else str(endpoint.host)) for endpoint in shell.workspace.get_objects(endpoints=True, scope=True)]
    tags = [cmd2.CompletionItem("!"+str(tag.name), "; ".join(str(e) for e in tag.endpoints)) for tag in shell.workspace.get_objects(tags=True, scope=True)]
    return endpoints+tags

def get_option_payload(shell):
    return Extensions.payloads.keys()

def get_option_connection(shell):
    return [cmd2.CompletionItem(str(connection), "" if connection.endpoint.host == None else str(connection.endpoint.host)) for connection in shell.workspace.get_objects(connections=True, scope=True)]

def get_search_fields_endpoint(shell):
    return shell.workspace.search_fields("Endpoint")

def get_search_fields_host(shell):
    return shell.workspace.search_fields("Host")

def get_open_tunnels(shell):
    return [cmd2.CompletionItem(str(tunnel.port), str(tunnel.connection)) for tunnel in shell.workspace.get_objects(tunnels=True)]

def get_run_targets(shell):
    return get_option_connection(shell) + get_option_host(shell) + get_option_endpoint(shell)

def get_host_or_local(shell):
    items = [cmd2.CompletionItem("local","BabooSSH host")]
    return items+[cmd2.CompletionItem(str(host.name), "; ".join(str(e) for e in host.endpoints)) for host in shell.workspace.get_objects(hosts=True, scope=True)]

def get_endpoint_or_host(shell):
    return get_option_host(shell) + get_option_endpoint(shell)

def get_tag(shell):
    return [cmd2.CompletionItem(str(tag.name), "; ".join(str(e) for e in tag.endpoints)) for tag in shell.workspace.get_objects(tags=True, scope=True)]

def get_all_objects(shell):
    return shell.workspace.get_objects(endpoints=True, creds=True, users=True, hosts=True)
