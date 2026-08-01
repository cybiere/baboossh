# Container A: Debian (systemd) + OpenSSH, password-only auth.
# Standalone target, reachable directly from the host on "hostnet".
FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd \
    && ssh-keygen -A

# Simulate a systemd host for baboossh's identify() command without actually
# running systemd as PID 1 inside the container.
RUN cat /proc/sys/kernel/random/uuid | tr -d '-' > /etc/machine-id

RUN useradd -m -s /bin/bash tester \
    && echo "tester:baboossh-test" | chpasswd

# Password auth only: no authorized_keys is ever installed for "tester", and
# pubkey auth is explicitly disabled so the intent is unambiguous rather than
# implicit in "no key exists".
RUN sed -i \
    -e 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' \
    -e 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication no/' \
    -e 's/^#\?PermitRootLogin.*/PermitRootLogin no/' \
    /etc/ssh/sshd_config

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]
