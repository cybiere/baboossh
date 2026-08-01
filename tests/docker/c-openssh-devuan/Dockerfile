# Container C: Devuan (Debian minus systemd, sysvinit) + OpenSSH, key-only
# auth. Reachable only by pivoting through container B, never from the host
# — enforced by an iptables rule inside this container (see entrypoint.sh),
# since Docker's own "internal: true" network flag only blocks the network's
# outbound internet access, not host-to-container reachability.
#
# Originally planned as TinySSH, then GNU lsh-server, but both are
# incompatible with paramiko (and so with baboossh) at the protocol level:
# TinySSH implements only the chacha20-poly1305 cipher, which paramiko has
# never implemented; lsh-server's only host-key algorithms are ssh-dss and
# spki, neither supported by paramiko (DSA support was dropped entirely).
# See todo.md. Reusing OpenSSH here still gives distro/init-system diversity
# (Devuan vs. Debian on container A) even though the SSH implementation is
# shared with A.
FROM devuan/devuan:chimaera

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server iproute2 iptables \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd \
    && ssh-keygen -A

COPY c-openssh-devuan/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# No /etc/machine-id: Devuan deliberately has no systemd, so a real Devuan
# host wouldn't have one either — this is the range's "identify() must not
# fail even when this file is missing" case.

RUN useradd -m -s /bin/bash tester \
    && usermod -L tester \
    && mkdir -p /home/tester/.ssh \
    && chown tester:tester /home/tester/.ssh \
    && chmod 700 /home/tester/.ssh

COPY --chown=tester:tester keys/test_id_ed25519.pub /home/tester/.ssh/authorized_keys
RUN chmod 600 /home/tester/.ssh/authorized_keys

# Key auth only: no password is set for "tester" (locked via usermod -L),
# and PasswordAuthentication is explicitly disabled so the intent is
# unambiguous.
RUN sed -i \
    -e 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' \
    -e 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' \
    -e 's/^#\?PermitRootLogin.*/PermitRootLogin no/' \
    /etc/ssh/sshd_config

EXPOSE 22
CMD ["/entrypoint.sh"]
