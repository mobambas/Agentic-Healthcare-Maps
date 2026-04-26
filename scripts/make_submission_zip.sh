#!/usr/bin/env bash
# One-line submission zip — run from the project root.
#
#   bash scripts/make_submission_zip.sh
#
# Excludes: .venv, .mlflow, .git, __pycache__, .DS_Store, .env (secrets),
# vllm_server.log, mlflow.db, .faiss, *.pyc, and the raw 10K
# data/vf_facilities.csv (judges can re-download from the Virtue
# Foundation link in docs/briefs/03_Serving_a_Nation.pdf).

set -euo pipefail

OUT="${1:-../agentic-healthcare-maps_submission.zip}"

zip -r "$OUT" . \
  -x "./.venv/*" "./.mlflow/*" "./.git/*" "*/__pycache__/*" "*.DS_Store" \
     "./data/vf_facilities.csv" "./.env" "./vllm_server.log" "./mlflow.db" \
     "./.faiss/*" "*.pyc"

echo "Wrote $(du -h "$OUT" | cut -f1) → $OUT"
