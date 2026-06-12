#!/usr/bin/env bash
# Start CAW TSS signer daemon(s) per mounted wallet profile, with retry + backoff.
#
# Key shares are MOUNTED at $PROFILES_DIR/<name>/ — each dir holds a profile's tss-node contents
# (the encrypted secrets db, the .password key-file, and configs/). NEVER bake key shares into the image.
# Only ONE node per identity may be connected to the CAW relay at a time: stop any other signer
# (e.g. a local Windows cobo-tss-node) for these wallets before starting this container.
#
# v2 (2026-06-12): replaced `wait -n` (which died on first exit) with a foreground retry loop
# that captures exit codes, dumps file logs, and backs off to break the relay phantom-session cycle.
set -uo pipefail

BIN=/usr/local/bin/cobo-tss-node
PROFILES_DIR=${PROFILES_DIR:-/keys}
mkdir -p "$PROFILES_DIR"

# ── config ──────────────────────────────────────────────────────────────────
MAX_RETRIES=${TSS_MAX_RETRIES:-5}        # give up after this many consecutive failures
INITIAL_BACKOFF=${TSS_INITIAL_BACKOFF:-60}  # seconds before first retry
MAX_BACKOFF=${TSS_MAX_BACKOFF:-300}         # cap on backoff (5 min)
HEALTHY_THRESHOLD=${TSS_HEALTHY_SECS:-300}  # if node runs >5 min, reset retry counter

# ── key-share reconstruction from env vars (Railway/Fly) ────────────────────
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

# ── helpers ─────────────────────────────────────────────────────────────────

# Dump file-logged output from the node (it switches to file logging after init).
# These logs survive crashes on the volume and are the ONLY way to see why it exited.
dump_file_logs() {
  local prof="$1" name="$2"
  shopt -s nullglob
  for lf in "${prof}logs/"*.log "${prof}node.log"; do
    [ -f "$lf" ] || continue
    local lines
    lines=$(wc -l < "$lf")
    echo "[tss][$name] ===== log: $lf ($lines lines, last 40) ====="
    tail -40 "$lf" | sed "s/^/[tss][$name] /"
  done
  shopt -u nullglob
}

# Prepare a profile directory (create expected subdirs, check writability).
prep_profile() {
  local prof="$1" name="$2"
  mkdir -p "${prof}logs" "${prof}recovery"
  [ -f "${prof}.tss-env" ] || printf 'prod' > "${prof}.tss-env"
  if ( touch "${prof}db/.wtest" 2>/dev/null && rm -f "${prof}db/.wtest" 2>/dev/null ); then
    echo "[tss][$name] db dir is writable"
  else
    echo "[tss][$name] WARN: ${prof}db is NOT writable — db init will fail"
  fi
}

# Run ONE signer profile in the foreground with retry + backoff.
# Returns 0 only if the node ran healthy (>HEALTHY_THRESHOLD seconds) and then exited (unlikely).
# Returns 1 if all retries exhausted.
run_signer_with_retry() {
  local prof="$1" name="$2"
  local retries=0 backoff=$INITIAL_BACKOFF

  while [ "$retries" -lt "$MAX_RETRIES" ]; do
    echo "[tss][$name] === attempt $((retries + 1))/$MAX_RETRIES (backoff=${backoff}s) ==="
    echo "[tss][$name] starting: cd $prof && $BIN start --caw --prod --key-file .password"

    local start_ts
    start_ts=$(date +%s)

    # Run in foreground — all output goes to stdout (captured by Railway logs).
    # Subshell contains the `cd` so it doesn't persist across retries or profile iterations.
    ( cd "$prof" && exec "$BIN" start --caw --prod --key-file .password )
    local exit_code=$?

    local end_ts elapsed
    end_ts=$(date +%s)
    elapsed=$((end_ts - start_ts))

    echo "[tss][$name] EXITED after ${elapsed}s with code ${exit_code}"

    # Dump file logs (the node writes detail to logs/ after init)
    dump_file_logs "$prof" "$name"

    # If it ran long enough, consider it healthy and reset retries
    if [ "$elapsed" -ge "$HEALTHY_THRESHOLD" ]; then
      echo "[tss][$name] ran for ${elapsed}s (>= ${HEALTHY_THRESHOLD}s) — was healthy, resetting retry counter"
      retries=0
      backoff=$INITIAL_BACKOFF
    else
      retries=$((retries + 1))
    fi

    if [ "$retries" -ge "$MAX_RETRIES" ]; then
      echo "[tss][$name] FATAL: $MAX_RETRIES consecutive short-lived exits. Giving up."
      return 1
    fi

    echo "[tss][$name] sleeping ${backoff}s before retry (to let relay release stale session)…"
    sleep "$backoff"
    # Exponential backoff, capped
    backoff=$((backoff * 2))
    [ "$backoff" -gt "$MAX_BACKOFF" ] && backoff=$MAX_BACKOFF
  done
}

# Collect all profile directories that have a .password file.
collect_profiles() {
  shopt -s nullglob
  local profs=()
  for prof in "$PROFILES_DIR"/*/; do
    [ -f "${prof}.password" ] && profs+=("$prof")
  done
  shopt -u nullglob
  printf '%s\n' "${profs[@]}"
}

# ── debug mode ──────────────────────────────────────────────────────────────
if [ "${TSS_DEBUG_SLEEP:-0}" = "1" ]; then
  for prof in "$PROFILES_DIR"/*/; do
    [ -f "${prof}.password" ] || continue
    prep_profile "$prof" "$(basename "$prof")"
  done
  echo "[tss] DEBUG_SLEEP=1: keys ready at $PROFILES_DIR. SSH in and run, e.g.:"
  echo "[tss]   cd $PROFILES_DIR/client && $BIN start --caw --prod --key-file .password"
  exec sleep infinity
fi

# ── main ────────────────────────────────────────────────────────────────────

# Wait for key shares if the volume is empty (Railway empty-volume bootstrapping).
profiles=$(collect_profiles)
if [ -z "$profiles" ]; then
  echo "[tss] no key shares under ${PROFILES_DIR} yet — polling every 10s."
  echo "[tss] populate via: railway ssh  then:  echo '<blob>' | base64 -d | tar -xz -C ${PROFILES_DIR}/client"
  while [ -z "$profiles" ]; do
    sleep 10
    profiles=$(collect_profiles)
  done
fi

echo "[tss] found profiles:"
echo "$profiles" | while read -r p; do echo "  - $p ($(basename "$p"))"; done

# Prepare all profiles
echo "$profiles" | while read -r prof; do
  prep_profile "$prof" "$(basename "$prof")"
done

# Run signers IN PARALLEL — each profile has a different identity (client vs provider),
# so they won't conflict on the relay. Each gets its own retry loop as a background process.
pids=()
while read -r prof; do
  name=$(basename "$prof")
  echo ""
  echo "[tss] ═══════════════════════════════════════════════════════════"
  echo "[tss] starting signer for profile: $name ($prof)"
  echo "[tss] ═══════════════════════════════════════════════════════════"
  run_signer_with_retry "$prof" "$name" &
  pids+=($!)
done <<< "$profiles"

echo ""
echo "[tss] started ${#pids[@]} signer(s) in background. Waiting…"
# Wait for all background processes. If any exit, the container stays alive (see below).
wait -n 2>/dev/null || true
echo "[tss] a signer exited. Keeping container alive for diagnostics."
echo "[tss] SSH in to investigate: railway ssh"
echo "[tss] Then restart the service: railway service restart"
exec sleep infinity
