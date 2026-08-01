# Container D: same Debian + OpenSSH + password-only setup as container A —
# its point isn't SSH-implementation diversity, it's network isolation (see
# compose.yml's "deadnet"). Gives baboossh's probe/path logic a real, live
# target that is genuinely unreachable, to exercise NoPathError. Isolation is
# enforced by an iptables rule inside the container (see entrypoint.sh),
# since Docker's "internal: true" alone doesn't block host-to-container
# reachability, only the network's own outbound internet access.
FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server iproute2 iptables \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd \
    && ssh-keygen -A

COPY d-unreachable/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN cat /proc/sys/kernel/random/uuid | tr -d '-' > /etc/machine-id

RUN useradd -m -s /bin/bash tester \
    && echo "tester:baboossh-test" | chpasswd

RUN sed -i \
    -e 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' \
    -e 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication no/' \
    -e 's/^#\?PermitRootLogin.*/PermitRootLogin no/' \
    /etc/ssh/sshd_config

EXPOSE 22
CMD ["/entrypoint.sh"]
