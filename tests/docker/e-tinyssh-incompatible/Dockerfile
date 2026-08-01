# Container E: TinySSH, directly reachable from the host on "hostnet".
#
# Deliberately included even though baboossh (via paramiko) cannot connect to
# it at all: TinySSH implements only the chacha20-poly1305 cipher, which
# paramiko has never supported (see todo.md). This container exists so that
# failure mode is part of the range instead of just a theory — baboossh
# should fail cleanly against it (a clear connection/negotiation error), not
# hang or crash. A real SSH client (e.g. a recent OpenSSH CLI) can connect to
# it fine, which is how the auth setup below was verified.
FROM devuan/devuan:chimaera

RUN apt-get update \
    && apt-get install -y --no-install-recommends tinysshd ucspi-tcp openssh-sftp-server \
    && rm -rf /var/lib/apt/lists/* \
    && tinysshd-makekey -q /etc/tinyssh/sshkeydir

RUN useradd -m -s /bin/bash tester \
    && usermod -L tester \
    && mkdir -p /home/tester/.ssh \
    && chown tester:tester /home/tester/.ssh \
    && chmod 700 /home/tester/.ssh

COPY --chown=tester:tester keys/test_id_ed25519.pub /home/tester/.ssh/authorized_keys
RUN chmod 600 /home/tester/.ssh/authorized_keys

EXPOSE 22
CMD ["tcpserver", "-HRDl0", "0.0.0.0", "22", "/usr/sbin/tinysshd", "-v", "-x", "sftp=/usr/lib/openssh/sftp-server", "--", "/etc/tinyssh/sshkeydir"]
