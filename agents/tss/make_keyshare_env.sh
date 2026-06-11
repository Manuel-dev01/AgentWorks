#!/usr/bin/env bash
# Emit base64 key-share blobs for the containerized TSS signer (Phase 6.5.4 Option B).
#
# Each blob is a gzip'd tar of the ESSENTIAL key material per profile (db/ + .password + configs/) —
# NOT the 48 MB full dir. The TSS container's entrypoint reconstructs these into /keys/<name>/ on first
# boot (see agents/tss/entrypoint.sh). Set them as Railway/Fly SECRETS, e.g.:
#   railway variables set "$(bash agents/tss/make_keyshare_env.sh ./keys | sed -n 1p)"
# or write to a (gitignored) file and import:  bash agents/tss/make_keyshare_env.sh ./keys > keyshare.env
#
# SECURITY: the output contains your MPC key shares. NEVER commit it; treat it like a private key.
set -euo pipefail

KEYS=${1:-./keys}
[ -d "$KEYS" ] || { echo "usage: $0 <keys-dir>   (each subdir = a wallet profile's tss-node contents)" >&2; exit 1; }

for prof in "$KEYS"/*/; do
  [ -f "${prof}.password" ] || continue
  name=$(basename "$prof" | tr '[:lower:]' '[:upper:]')
  blob=$(tar -czf - -C "$prof" db .password configs | base64 -w0 2>/dev/null || tar -czf - -C "$prof" db .password configs | base64)
  printf 'TSS_KEYSHARE_%s_B64=%s\n' "$name" "$blob"
done
