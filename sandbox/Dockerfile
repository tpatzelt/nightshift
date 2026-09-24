# syntax=docker/dockerfile:1
# NIGHTSHIFT agent image. Built by the orchestrator ON THE DIND DAEMON, never on
# the host daemon. Every agent container is thrown away after a single run.
ARG NS_NODE_IMAGE
ARG NS_UV_IMAGE
FROM ${NS_UV_IMAGE} AS uvbin

FROM ${NS_NODE_IMAGE}

ARG NS_CLAUDE_CODE_VERSION
ARG NS_AGENT_PYTHON

# Deliberately no curl, wget, ssh or netcat: the only way out is the squid proxy,
# and the package managers below are the only things that need it.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git python3 python3-venv python3-pip python3-dev \
      build-essential ca-certificates ripgrep jq less \
 && rm -rf /var/lib/apt/lists/*

# uv, pinned by digest, and the current CPython it manages. Debian's python3
# (3.11) stays in /usr/bin for system tooling; /usr/local/bin comes first on PATH,
# so an agent typing "python3" gets the modern interpreter.
COPY --from=uvbin /uv /uvx /usr/local/bin/
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    UV_NO_PROGRESS=1 \
    UV_LINK_MODE=copy
RUN uv python install ${NS_AGENT_PYTHON} \
 && ln -sf "$(uv python find ${NS_AGENT_PYTHON})" /usr/local/bin/python3 \
 && ln -sf /usr/local/bin/python3 /usr/local/bin/python \
 && chmod -R a+rX /opt/uv-python

RUN npm install -g @anthropic-ai/claude-code@${NS_CLAUDE_CODE_VERSION} \
 && npm cache clean --force

# Managed policy and guard hook: root-owned, read-only, outside /work so the
# agent can neither edit them nor delete them.
COPY --chown=root:root --chmod=444 managed-settings.json /etc/claude-code/managed-settings.json
COPY --chown=root:root --chmod=555 hooks/guard.py /opt/guard/guard.py
# COPY creates parent directories mode 0700, which would make the policy file
# unreadable to uid 10001 and silently disable it. The agent must be able to
# traverse in and read, but not write.
RUN chmod 755 /etc/claude-code /opt/guard

# The agent runs as uid 1000 because /work is a bind mount owned by Tim (uid 1000)
# on the host: the orchestrator prepares the git worktree there and the agent has
# to commit into it, and whatever it writes must stay editable over SSH. The node
# image ships its own uid 1000, so that account is removed first.
RUN userdel -r node 2>/dev/null || true \
 && useradd --uid 1000 --create-home --shell /bin/bash agent \
 && mkdir -p /work && chown 1000:1000 /work

ENV DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    DISABLE_TELEMETRY=1 \
    DISABLE_ERROR_REPORTING=1 \
    npm_config_update_notifier=false \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/agent

USER 1000:1000
WORKDIR /work
