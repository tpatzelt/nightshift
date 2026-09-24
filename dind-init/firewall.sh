#!/bin/sh
# NIGHTSHIFT jail firewall. Applied INSIDE the dind container's network namespace,
# so it never touches the host's iptables. Idempotent: re-applied on every start.
#
#   usage: firewall.sh [jail_subnet] [proxy_ip] [proxy_port]
set -eu

JAIL_SUBNET="${1:-172.30.99.0/24}"
PROXY_IP="${2:-172.30.99.2}"
PROXY_PORT="${3:-3128}"
CHAIN=NIGHTSHIFT_JAIL

# Docker creates DOCKER-USER for exactly this purpose and consults it before its
# own rules, so what we put here survives container and network churn.
iptables -N "$CHAIN" 2>/dev/null || iptables -F "$CHAIN"
iptables -C DOCKER-USER -j "$CHAIN" 2>/dev/null || iptables -I DOCKER-USER 1 -j "$CHAIN"

# Replies to connections the jail legitimately opened.
iptables -A "$CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
# The single permitted destination: the proxy's CONNECT port.
iptables -A "$CHAIN" -s "$JAIL_SUBNET" -d "$PROXY_IP" -p tcp --dport "$PROXY_PORT" -j RETURN
# Everything else the jail tries to reach — LAN, other containers, the DinD API,
# the orchestrator, the internet direct — is dropped.
iptables -A "$CHAIN" -s "$JAIL_SUBNET" -j DROP
# And nothing may open a new connection *into* the jail either.
iptables -A "$CHAIN" -d "$JAIL_SUBNET" -j DROP

echo "firewall applied: jail=$JAIL_SUBNET proxy=$PROXY_IP:$PROXY_PORT"
iptables -S "$CHAIN"
