# syntax=docker/dockerfile:1
ARG NS_DIND_IMAGE
ARG NS_PYTHON_IMAGE

# Take the docker CLI + buildx from the same pinned dind image the daemon runs,
# so client and server versions always match and there is no apt repo to trust.
FROM ${NS_DIND_IMAGE} AS dockercli

FROM ${NS_PYTHON_IMAGE}

COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins/docker-buildx \
                      /usr/local/libexec/docker/cli-plugins/docker-buildx

RUN apt-get update \
 && apt-get install -y --no-install-recommends git jq tzdata ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir PyYAML==6.0.2

# uid 1000 matches Tim on the host, so files written to the /data bind mount
# come out owned by him and stay editable over SSH.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin ns

WORKDIR /app
COPY --chown=root:root nightshift.py plan.py gates.py healthcheck.py config.yaml ./
COPY --chown=root:root prompts/ ./prompts/
COPY --chown=root:root tests/ ./tests/

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER ns
ENTRYPOINT ["python3", "/app/nightshift.py"]
CMD ["run"]
