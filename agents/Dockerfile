# AgentWorks autonomous agent service (Phase 6.5.4) — the cloud-deployable HTTP front for the
# autonomous open-marketplace agents. Holds NO key material; talks to the CAW cloud API over HTTPS.
# On-chain signing happens via the TSS node on the CAW relay (see Dockerfile.tss / docs/DEPLOY_AGENTS.md).
#
# Build from the REPO ROOT (context must include contracts/out for the v2 ABI):
#   docker build -f agents/Dockerfile -t agentworks-agent .
# Run:
#   docker run --env-file .env -p 8000:8000 agentworks-agent

FROM python:3.12-slim

# Node is required by the Irys uploader (agents/irys/upload.mjs uses @irys/upload).
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (cached layer)
COPY agents/requirements.txt /app/agents/requirements.txt
RUN pip install --no-cache-dir -r /app/agents/requirements.txt

# Irys Node deps (cached layer; node_modules is .dockerignored so this installs fresh)
COPY agents/irys/package.json agents/irys/package-lock.json /app/agents/irys/
RUN cd /app/agents/irys && (npm ci --omit=dev || npm install --omit=dev)

# Application code (includes the vendored v2 ABI at agents/abi/AgentWorksEscrowV2.json,
# which escrow_v2.py prefers — contracts/out is gitignored and not shipped).
COPY agents/ /app/agents/

WORKDIR /app/agents
ENV PYTHONUNBUFFERED=1 PORT=8000
EXPOSE 8000

# Lightweight liveness check
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health').read()" || exit 1

CMD ["python", "server.py"]
