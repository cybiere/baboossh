endpoint command
================

Manage [endpoint objects]([Object]-Endpoint).

# Subcommands

If no subcommand is provided, the default behaviour is `list`.

## `list`

List endpoints in workspace in a tabular view.

## `add <ip> [<port>]`

### Arguments

 - `<ip>`: a valid IPv4 or IPv6 IP address.
 - `<port>`: an integer between 0 and 65535.

Add endpoint `<ip>:<port>` to the workspace. If port is not specified, default value is 22.

The command will ask it must add a [Path]([Object]-Path) from `Local` to the new Endpoint. If you can reach the endpoint from your current host, answer `Yes`, else `No`.

## `delete <endpoint>`

### Arguments

 - `<endpoint>`: a registered endpoint in the workspace.

Delete endpoint `<endpoint>` from the workspace. Recursively delete [Paths]([Object]-Path) and [Connections]([Object]-Connection) to the endpoint, as well as associated [Host]([Object]-Host) if the endpoint was the last to its Host.

