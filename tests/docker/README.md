# baboossh test range

A small Docker Compose SSH range for exercising `baboossh`'s pivoting, multiple SSH server implementations, multiple auth methods, and `identify()`'s robustness when expected commands/files aren't present on the target. Wired into the automated test suite as an opt-in group — see "Automated tests" below — and see `todo.md` for what's still untested.

## Topology

```
                    host machine
                         │
              hostnet (10.10.0.0/24, bridge)
       ┌─────────────────┼─────────────────┐
  10.10.0.2          10.10.0.3         10.10.0.4
 [A: openssh]     [B: dropbear]     [E: tinysshd]
  debian            alpine           devuan
  password          gateway ──┐      paramiko-INCOMPATIBLE
                               │      (see "Container E" below)
                    pivotnet (10.10.1.0/24, internal)
                               │
                         10.10.1.4
                    [C: openssh, devuan]
                     key-only, pivot-only


              deadnet (10.10.2.0/24, internal, solo member)
                               │
                         10.10.2.2
                    [D: openssh, debian]
                     firewalled off from everyone
```

| | Distro | SSH server | Auth | Reachable from host? |
|---|---|---|---|---|
| **A** | Debian (systemd) | OpenSSH | password only | yes — `10.10.0.2:22` |
| **B** | Alpine (no systemd) | Dropbear | password + key | yes — `10.10.0.3:22`, also the pivot gateway to C |
| **C** | Devuan (no systemd) | OpenSSH | key only | **no** — only from B, see below |
| **D** | Debian (systemd) | OpenSSH | password | **no** — from nowhere at all |
| **E** | Devuan (no systemd) | TinySSH | key only | yes — `10.10.0.4:22`, but see the compatibility note below |

`internal: true` on the `pivotnet`/`deadnet` Docker networks is **not** sufficient by itself to block the host — Docker always gives the host a direct route to any bridge network it creates; `internal: true` only removes that network's outbound-to-internet route. C and D each run their own `iptables` rule (in `entrypoint.sh`) to actually enforce this: C only accepts port 22 connections from B's pivotnet IP (`10.10.1.3`); D drops all port 22 connections unconditionally. This is why both containers need `cap_add: [NET_ADMIN]` in `compose.yml`.

## Credentials

Fixed, committed, obviously-fake test values — **do not reuse these anywhere real**:
- Password (A, B): `baboossh-test`
- Key (B, C, E): `keys/test_id_ed25519` (private key, already `chmod 600`), `keys/test_id_ed25519.pub`
- User on every container: `tester` (non-root; root SSH login is disabled everywhere)

## Container E and the ChaCha20-Poly1305 compatibility gap

Container E is deliberately included even though **`baboossh` cannot connect to it at all**. `paramiko` (which `baboossh` uses) has no `chacha20-poly1305@openssh.com` cipher implementation, and TinySSH implements *only* that cipher by design — there's no overlapping algorithm. A real SSH client (e.g. `ssh -i keys/test_id_ed25519 tester@10.10.0.4`) connects to it fine; `baboossh`/paramiko will fail with a clear `IncompatiblePeer: Incompatible ssh server (no acceptable ciphers)` error. See `todo.md` for the full writeup — this container exists specifically so that failure mode is something you can see and verify (fails cleanly, doesn't hang), not just a theoretical concern.

(TinySSH was originally planned for container C too. GNU `lsh-server` was tried as a second alternative and also failed — its only host-key algorithms are `ssh-dss`/`spki`, and paramiko dropped DSA support entirely. Both incompatibilities are documented in `todo.md`.)

## Usage

```sh
cd tests/docker
docker compose up --build -d
```

Bring it down (and remove the networks) with `docker compose down`.

## Walkthrough with baboossh

Run `baboossh` from the host (wherever it's installed — `uv run baboossh` from the repo root):

```
workspace add dockertest
workspace use dockertest

# Container A — direct, password auth
endpoint add 10.10.0.2 22
user add tester
creds add password
  (username: tester, password: baboossh-test)
connect tester:#1@10.10.0.2:22
  # identify() should populate a Host with a real /etc/machine-id (systemd, Debian)

# Container B — direct, key auth, and the pivot gateway
endpoint add 10.10.0.3 22
creds add privkey
  (path: tests/docker/keys/test_id_ed25519)
connect tester:#2@10.10.0.3:22
  # identify() should show no /etc/machine-id (Alpine, no systemd)

# Container C — only reachable by pivoting through B
endpoint add 10.10.1.4 22
path add <B's host name> 10.10.1.4:22
connect tester:#2@10.10.1.4:22
  # should succeed via the path through B; identify() should show no
  # /etc/machine-id either (Devuan, no systemd)
probe 10.10.1.4:22
  # try this BEFORE adding the path, from a fresh workspace, to confirm a
  # direct probe fails and pivoting is genuinely required

# Container D — exercises NoPathError
endpoint add 10.10.2.2 22
probe 10.10.2.2:22
  # should eventually report no path found — but be patient. probe() tries
  # every known Host as a candidate gateway before giving up, and against a
  # genuinely unreachable target every one of those attempts has to time out
  # first; this can take a couple of minutes, not because anything is stuck.
  # See todo.md.

# Container E — exercises baboossh's behavior against an incompatible server
endpoint add 10.10.0.4 22
connect tester:#2@10.10.0.4:22
  # should fail cleanly (see "Container E" section above), not hang
```

Then exercise payloads (`exec`, `shell`, `getfile`, `putfile`, `gather`) against whichever connections succeeded, to confirm they work correctly under the non-root `tester` account.

## Automated tests

The scenarios in the walkthrough above are also covered by `tests/test_docker_range.py`. They're opt-in — not part of the default `uv run pytest` / CI run — since they need Docker and take real wall-clock time to build images and perform live SSH handshakes:

```sh
uv run pytest --run-docker -v tests/test_docker_range.py
```

This builds and tears down the whole range itself (session-scoped fixture), so `docker compose up` beforehand isn't required. Without `--run-docker`, these tests are skipped and the rest of the suite is unaffected.

## SFTP subsystem support

`getfile`/`putfile` use paramiko's SFTP client. All three SSH servers in this range (OpenSSH, Dropbear, and — separately — TinySSH on container E) were confirmed to support the SFTP subsystem correctly during this range's construction, so no known gaps there.
