# Container B: Alpine (no systemd, musl, OpenRC) + Dropbear, password + key
# auth. Host-reachable on "hostnet" AND the pivot gateway to C on "pivotnet".
FROM alpine:3.19

RUN apk add --no-cache dropbear dropbear-scp openssh-sftp-server iproute2 \
    && mkdir -p /etc/dropbear \
    && dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key \
    && dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key \
    && ln -s /sbin/ip /usr/bin/ip

RUN adduser -D -s /bin/sh tester \
    && echo "tester:baboossh-test" | chpasswd \
    && mkdir -p /home/tester/.ssh \
    && chown tester:tester /home/tester/.ssh \
    && chmod 700 /home/tester/.ssh

COPY --chown=tester:tester keys/test_id_ed25519.pub /home/tester/.ssh/authorized_keys
RUN chmod 600 /home/tester/.ssh/authorized_keys

# No /etc/machine-id is created here: Alpine has no systemd and wouldn't have
# one for real, which is the point of this container in the range.

EXPOSE 22
# -F: foreground, -E: log to stderr. Neither -s (disable password logins) nor
# -j/-k (disable local/remote TCP forwarding) is passed, since this container
# must support both password and key auth, and must support the "direct-tcpip"
# channel type baboossh uses to pivot through it to container C.
CMD ["/usr/sbin/dropbear", "-F", "-E", "-p", "22"]
