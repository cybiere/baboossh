# Testing follow-up

The initial test suite (`tests/`) covers `Db`, `Workspace` lifecycle, `Path` add/del/find, `Tag`, and `Extensions.load()`. Deliberately out of scope for that first pass — tracked here for later:

- **`shell/` command handlers** — none of the ~20 `do_*` cmd2 commands (split across `baboossh/shell/*.py`) are tested. Needs `cmd2`'s own test harness patterns (`cmd2.Cmd`'s `app.onecmd(...)` / output-capture fixtures) rather than calling `Workspace` methods directly.
- **`connection.py` (SSH/paramiko)** — untested. Needs mocking a real SSH transport (e.g. `paramiko.Transport`) rather than hitting a live host.
- **`ext_dir/` extension plugins** — untested. Payload/auth/import/export plugins do real subprocess and filesystem operations (`payload_gather.py`, `payload_putfile.py`, etc.) and need their own mocking strategy; `test_extensions.py` only covers that `Extensions.load()` discovers and registers them, not their actual behavior.
- **Remaining `Unique`-metaclass models** — `Host`, `Endpoint`, `User`, `Creds`, `Connection` don't have dedicated test files yet. `test_tag.py` and `test_path.py` exercise them incidentally as fixtures, but their own CRUD/search methods (`find_all`/`save`/`delete`/`*_search`) aren't directly tested the way `Tag`'s are.
- **`workspace/` mixins' remaining public methods** — `enum_probe`, `enum_connect`, `enum_run`, `probe`, `connect`, `run`, `tunnel_open`/`tunnel_close`, `identify_object`, `scope`, `get_objects` (in `baboossh/workspace/*.py`) are untested. Several of these depend on live SSH connections or tunnels and will need mocking similar to `connection.py`.
- **CI matrix** — the workflow currently runs a single Python version (whatever `uv sync` resolves by default). Consider a version matrix once the suite is established, especially since `requires-python = ">=3.11"` claims broader support than is currently verified.

# Type hints follow-up

`__all__` was added to every wildcard-imported module, and type hints were added to the 7 model classes (`Tag`, `Path`, `Endpoint`, `Host`, `User`, `Creds`, `Connection`) plus `Db`/`Extensions`/`Tunnel`/`utils.py`'s plain functions. Deliberately out of scope for that pass:

- **`workspace/` mixins** (split from the former 927-line `workspace.py` into `baboossh/workspace/*.py`) — not typed. Pyright already flags several pre-existing Optional-handling issues in it (e.g. `Host | None` return values used without a None-check). Accurately typing it will surface these as real errors, and it has no dedicated tests to catch a fix gone wrong — type this only after adding test coverage for it, not as a drive-by.
- **`shell/` mixins' `do_*` cmd2 command handlers** (split from the former 1220-line `shell.py` into `baboossh/shell/*.py`) — not typed. `cmd2`'s `Statement`/argparse-namespace typing is a different, lower-value effort than the model-class work.
- **The `Unique` metaclass** (`utils.py`) — not typed. Metaclass typing (`__call__`/`__new__` interacting with per-workspace instance caching) is inherently advanced; `Self` usage in the classes that use it as their metaclass works fine without this.
- **Full `mypy` CI enforcement** — hints were added and spot-checked file-by-file with `mypy --python-version 3.11`, but no CI gate was wired up. Doing so now would likely fail on `workspace/`'s and `shell/`'s untyped state and on genuinely unfixable noise (no type stubs exist for `paramiko`/`tabulate`).
- **CRUD base-class extraction** (the original audit finding this work was scoped down from) — still deferred, still gated on adding tests for `Host`/`Endpoint`/`User`/`Creds`/`Connection` first (see above).
