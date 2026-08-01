#!/bin/sh
# Container-level firewall: only accept SSH from B's pivotnet IP (10.10.1.3),
# so this container is only ever reachable by pivoting through B, never
# directly (including from the Docker host, which is otherwise always able
# to reach any bridge network it creates — internal:true alone doesn't stop
# that, only iptables inside the container does).
set -e
iptables -A INPUT -p tcp --dport 22 -s 10.10.1.3 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j DROP
exec /usr/sbin/sshd -D -e
