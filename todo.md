# Testing follow-up

The initial test suite (`tests/`) covers `Db`, `Workspace` lifecycle, `Path` add/del/find, `Tag`, and `Extensions.load()`. Deliberately out of scope for that first pass — tracked here for later:

- **`shell.py` command handlers** — none of the ~80 `do_*` cmd2 commands are tested. Needs `cmd2`'s own test harness patterns (`cmd2.Cmd`'s `app.onecmd(...)` / output-capture fixtures) rather than calling `Workspace` methods directly.
- **`connection.py` (SSH/paramiko)** — untested. Needs mocking a real SSH transport (e.g. `paramiko.Transport`) rather than hitting a live host.
- **`ext_dir/` extension plugins** — untested. Payload/auth/import/export plugins do real subprocess and filesystem operations (`payload_gather.py`, `payload_putfile.py`, etc.) and need their own mocking strategy; `test_extensions.py` only covers that `Extensions.load()` discovers and registers them, not their actual behavior.
- **Remaining `Unique`-metaclass models** — `Host`, `Endpoint`, `User`, `Creds`, `Connection` don't have dedicated test files yet. `test_tag.py` and `test_path.py` exercise them incidentally as fixtures, but their own CRUD/search methods (`find_all`/`save`/`delete`/`*_search`) aren't directly tested the way `Tag`'s are.
- **`workspace.py`'s remaining public methods** — `enum_probe`, `enum_connect`, `enum_run`, `probe`, `connect`, `run`, `tunnel_open`/`tunnel_close`, `identify_object`, `scope`, `get_objects` are untested. Several of these depend on live SSH connections or tunnels and will need mocking similar to `connection.py`.
- **CI matrix** — the workflow currently runs a single Python version (whatever `uv sync` resolves by default). Consider a version matrix once the suite is established, especially since `requires-python = ">=3.9"` claims broader support than is currently verified.
