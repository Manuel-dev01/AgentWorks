#!/usr/bin/env bash
# Start a CAW TSS signer daemon per mounted wallet profile, then wait.
#
# Key shares are MOUNTED at $PROFILES_DIR/<name>/ — each dir holds a profile's tss-node contents
# (the encrypted secrets db, the .password key-file, and configs/). NEVER bake key shares into the image.
# Only ONE node per identity may be connected to the CAW relay at a time: stop any other signer
# (e.g. a local Windows cobo-tss-node) for these wallets before starting this container.
set -euo pipefail

BIN=/usr/local/bin/cobo-tss-node
PROFILES_DIR=${PROFILES_DIR:-/keys}
mkdir -p "$PROFILES_DIR"

# Railway/Fly provisioning: if a profile isn't already on the volume but its key material was supplied
# as base64 secret env vars (a gzip'd tar of db/ .password configs/), reconstruct it into
# $PROFILES_DIR/<name>/ on first boot. Subsequent boots reuse the persisted volume contents.
# Supports a single var TSS_KEYSHARE_<NAME>_B64 OR ordered chunks TSS_KEYSHARE_<NAME>_B64_00,_01,…
# (Railway caps each variable at 32KB, so large key shares are split into chunks.)
for NAME in $(env | sed -nE 's/^TSS_KEYSHARE_([A-Z0-9]+)_B64(_[0-9]+)?=.*/\1/p' | sort -u); do
  name=$(printf '%s' "$NAME" | tr '[:upper:]' '[:lower:]')
  dest="$PROFILES_DIR/$name"
  [ -f "$dest/.password" ] && continue
  echo "[tss] reconstructing key share '$name' from env (TSS_KEYSHARE_${NAME}_B64*)"
  blob=""
  single="TSS_KEYSHARE_${NAME}_B64"
  [ -n "${!single:-}" ] && blob="${!single}"
  for var in $(env | sed -nE "s/^(TSS_KEYSHARE_${NAME}_B64_[0-9]+)=.*/\1/p" | sort); do
    blob="${blob}${!var}"
  done
  mkdir -p "$dest"
  printf '%s' "$blob" | base64 -d | tar -xz -C "$dest" || echo "[tss] WARN: reconstruct of '$name' failed"
done

# Surface file-logged errors from a previous (crashed) iteration: after the node loads its config it
# logs detail to logs/cobo-tss-node-*.log, which a fast crash-loop hides from stdout. Dump them once.
dump_prev_logs() {
  shopt -s nullglob
  local prof lf
  for prof in "$PROFILES_DIR"/*/; do
    for lf in "${prof}logs/"*.log "${prof}node.log"; do
      [ -f "$lf" ] || continue
      echo "[tss] ===== previous log $lf (tail) ====="
      tail -25 "$lf" | sed "s/^/[prev $(basename "$prof")] /"
    done
  done
}

start_signers() {
  shopt -s nullglob
  local started=0 prof name
  for prof in "$PROFILES_DIR"/*/; do
    if [ -f "${prof}.password" ]; then
      name=$(basename "$prof")
      # The node's config enables FILE logging to logs/ and may read recovery/ + .tss-env; the chunked
      # reconstruction only ships db/.password/configs, so create the rest the node expects.
      mkdir -p "${prof}logs" "${prof}recovery"
      [ -f "${prof}.tss-env" ] || printf 'prod' > "${prof}.tss-env"
      # writability preflight — SQLite must write the db + its journal/wal alongside secrets.db
      if ( touch "${prof}db/.wtest" 2>/dev/null && rm -f "${prof}db/.wtest" 2>/dev/null ); then
        echo "[tss][$name] db dir is writable"
      else
        echo "[tss][$name] WARN: ${prof}db is NOT writable — db init will fail"
      fi
      echo "[tss] starting signer for profile: ${prof}"
      # Tee the node's own stdout/stderr to a file on the volume (survives crashes) AND to the
      # container log (tagged, unbuffered) — a bare `&` subprocess's output is otherwise easily lost.
      ( cd "$prof" && exec "$BIN" start --caw --prod --key-file .password ) 2>&1 \
        | stdbuf -oL tee -a "${prof}node.log" | sed -u "s/^/[$name] /" &
      started=$((started + 1))
    fi
  done
  return "$started"
}

# Debug: skip starting signers and stay alive so you can `railway ssh` in and run the node by hand.
if [ "${TSS_DEBUG_SLEEP:-0}" = "1" ]; then
  for prof in "$PROFILES_DIR"/*/; do
    [ -f "${prof}.password" ] || continue
    mkdir -p "${prof}logs" "${prof}recovery"; [ -f "${prof}.tss-env" ] || printf 'prod' > "${prof}.tss-env"
  done
  echo "[tss] DEBUG_SLEEP=1: keys ready at $PROFILES_DIR. SSH in and run, e.g.:"
  echo "[tss]   cd $PROFILES_DIR/client && /usr/local/bin/cobo-tss-node start --caw --prod --key-file .password"
  exec sleep infinity
fi

dump_prev_logs
start_signers
started=$?

# Railway/empty-volume friendly: if no key shares are present yet, STAY ALIVE and poll, so you can
# populate the mounted volume via `railway ssh` (pipe base64 blobs into $PROFILES_DIR/<name>/) without
# the container crash-looping. Once keys appear, start the signers.
while [ "$started" -eq 0 ]; do
  echo "[tss] no key shares under ${PROFILES_DIR} yet — waiting. Populate via:"
  echo "[tss]   railway ssh  then:  echo '<blob>' | base64 -d | tar -xz -C ${PROFILES_DIR}/client   (and /provider)"
  sleep 10
  start_signers
  started=$?
done

echo "[tss] started ${started} signer(s); connected to the CAW relay. Waiting…"
wait -n
echo "[tss] a signer exited — stopping container so the orchestrator can restart it."
