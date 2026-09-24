# syntax=docker/dockerfile:1
# Tiny helper that applies DinD's own iptables rules. Run on the INNER daemon with
# --network host (inside DinD that means DinD's network namespace) and NET_ADMIN.
# The agent image deliberately does not contain iptables.
ARG NS_ALPINE_IMAGE
FROM ${NS_ALPINE_IMAGE}
RUN apk add --no-cache iptables ip6tables
ENTRYPOINT ["/bin/sh"]
