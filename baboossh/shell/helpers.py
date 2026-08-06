"""Shared cmd2 completion providers and command categories for the Shell commands.

Every ``choices_provider`` used by the various command sections lives here as a
plain function taking the ``Shell`` instance explicitly (cmd2 supports this
calling convention natively, passing the app instance as the first positional
argument) so any section can reference any getter uniformly, regardless of
how many sections use it.
"""

import os
from collections.abc import KeysView
from typing import TYPE_CHECKING, Protocol, cast

import cmd2

from baboossh import Connection, Creds, Endpoint, Host, Tag, Tunnel, User
from baboossh.utils import WORKSPACES_DIR
from baboossh.extensions import Extensions

if TYPE_CHECKING:
    from baboossh.workspace import Workspace

    class _Shell(Protocol):
        workspace: Workspace

CMD_CAT_OBJ = "Object management"
CMD_CAT_CON = "Connecting hosts"
CMD_CAT_WSP = "Workspace management"


def get_option_creds(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    creds_list = cast("list[Creds]", shell.workspace.get_objects(creds=True, scope=True))
    return [cmd2.CompletionItem("#"+str(creds.id), display_meta=creds.obj.toList()) for creds in creds_list]

def get_option_host(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    hosts = cast("list[Host]", shell.workspace.get_objects(hosts=True, scope=True))
    return [cmd2.CompletionItem(str(host.name), display_meta="; ".join(str(e) for e in host.endpoints)) for host in hosts]

def get_arg_workspaces(shell: "_Shell") -> list[str]:
    return [name for name in os.listdir(WORKSPACES_DIR) if os.path.isdir(os.path.join(WORKSPACES_DIR, name))]

def get_option_gateway(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    return get_host_or_local(shell)

def get_option_user(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    users = cast("list[User]", shell.workspace.get_objects(users=True, scope=True))
    return [cmd2.CompletionItem(str(user), display_meta=str(user)) for user in users]

def get_option_endpoint(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    endpoints = cast("list[Endpoint]", shell.workspace.get_objects(endpoints=True, scope=True))
    return [cmd2.CompletionItem(str(endpoint), display_meta="" if endpoint.host == None else str(endpoint.host)) for endpoint in endpoints]

def get_option_endpoint_tag(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    endpoints_list = cast("list[Endpoint]", shell.workspace.get_objects(endpoints=True, scope=True))
    endpoints = [cmd2.CompletionItem(str(endpoint), display_meta="" if endpoint.host == None else str(endpoint.host)) for endpoint in endpoints_list]
    tags_list = cast("list[Tag]", shell.workspace.get_objects(tags=True, scope=True))
    tags = [cmd2.CompletionItem("!"+str(tag.name), display_meta="; ".join(str(e) for e in tag.endpoints)) for tag in tags_list]
    return endpoints+tags

def get_option_payload(shell: "_Shell") -> "KeysView[str]":
    return Extensions.payloads.keys()

def get_option_connection(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    connections = cast("list[Connection]", shell.workspace.get_objects(connections=True, scope=True))
    return [cmd2.CompletionItem(str(connection), display_meta="" if connection.endpoint.host == None else str(connection.endpoint.host)) for connection in connections]

def get_search_fields_endpoint(shell: "_Shell") -> list[str]:
    return shell.workspace.search_fields("Endpoint")

def get_search_fields_host(shell: "_Shell") -> list[str]:
    return shell.workspace.search_fields("Host")

def get_open_tunnels(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    tunnels = cast("list[Tunnel]", shell.workspace.get_objects(tunnels=True))
    return [cmd2.CompletionItem(str(tunnel.port), display_meta=str(tunnel.connection)) for tunnel in tunnels]

def get_run_targets(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    return get_option_connection(shell) + get_option_host(shell) + get_option_endpoint(shell)

def get_host_or_local(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    hosts = cast("list[Host]", shell.workspace.get_objects(hosts=True, scope=True))
    items = [cmd2.CompletionItem("local", display_meta="BabooSSH host")]
    return items+[cmd2.CompletionItem(str(host.name), display_meta="; ".join(str(e) for e in host.endpoints)) for host in hosts]

def get_endpoint_or_host(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    return get_option_host(shell) + get_option_endpoint(shell)

def get_tag(shell: "_Shell") -> "list[cmd2.CompletionItem]":
    tags = cast("list[Tag]", shell.workspace.get_objects(tags=True, scope=True))
    return [cmd2.CompletionItem(str(tag.name), display_meta="; ".join(str(e) for e in tag.endpoints)) for tag in tags]

def get_all_objects(shell: "_Shell") -> list[object]:
    return shell.workspace.get_objects(endpoints=True, creds=True, users=True, hosts=True)
