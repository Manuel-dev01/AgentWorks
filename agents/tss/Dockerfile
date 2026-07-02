# AgentWorks TSS signer (Phase 6.5.4) - runs the Linux CAW TSS node(s) that co-sign for the agent
# wallets. Holds the MPC key share, so prefer a host YOU control. Key shares are MOUNTED at /keys,
# NEVER baked into the image. The Linux binary availability was verified in docs/FACTS.md (6.5.0).
#
# Context = REPO ROOT (so it works identically on Railway, which builds from the repo root).
# Local build:    docker build -f agents/tss/Dockerfile -t agentworks-tss .
# Railway build:  set the service var RAILWAY_DOCKERFILE_PATH=agents/tss/Dockerfile, then `railway up`.
# Run:  docker run -v /abs/path/to/keys:/keys agentworks-tss   (each /keys/<name>/ = a profile's tss-node dir)
# NOTE: only ONE node per identity may be on the CAW relay at a time - stop the local Windows signer first.

FROM debian:bookworm-slim

ARG TSS_OS=linux
ARG TSS_ARCH=amd64
# Download the official Linux CAW TSS node (source: the CAW install.sh - see docs/FACTS.md 6.5.0).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "https://download.tss.cobo.com/binary-release/latest/cobo-tss-node-${TSS_OS}-${TSS_ARCH}.tar.gz" -o /tmp/tss.tgz \
    # The tarball extracts into a directory (cobo-tss-node/{cobo-tss-node, SHA256SUMS, configs/}),
    # so locate the actual binary and install it as the file /usr/local/bin/cobo-tss-node.
    && mkdir -p /opt/tss && tar -xzf /tmp/tss.tgz -C /opt/tss \
    && install -m 0755 "$(find /opt/tss -type f -name cobo-tss-node | head -1)" /usr/local/bin/cobo-tss-node \
    && rm -rf /tmp/tss.tgz \
    && /usr/local/bin/cobo-tss-node --help >/dev/null 2>&1 || /usr/local/bin/cobo-tss-node version >/dev/null 2>&1 || true

COPY agents/tss/entrypoint.sh /usr/local/bin/entrypoint.sh
# Normalize line endings (a CRLF checkout would make the shebang `#!/usr/bin/env bash\r`, which Linux
# resolves to a nonexistent `bash\r` — "env: 'bash\r': No such file or directory" — so no signer starts).
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh

ENV PROFILES_DIR=/keys
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
