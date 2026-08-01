#!/bin/sh
# Container-level firewall: drop all incoming SSH connections unconditionally
# — this container has no legitimate path from anywhere. Docker's
# "internal: true" network flag alone isn't enough, since the Docker host
# can still reach any bridge network it creates; only iptables inside the
# container actually blocks it.
set -e
iptables -A INPUT -p tcp --dport 22 -j DROP
exec /usr/sbin/sshd -D -e
