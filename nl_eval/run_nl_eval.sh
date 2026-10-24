#!/usr/bin/env bash
# One-shot NL integrity test on a fresh RunPod pod.
#
#   export HF_TOKEN=hf_...
#   apt-get update && apt-get install -y tmux
#   tmux new -s nl
#   bash run_nl_eval.sh
#
# Overrides:
#   MODELS="qwen3 lfm2"      subset of: qwen3 lfm2 hermes3 gpt2
#   MAX_TOKENS=20000         quick run on the first N WikiText tokens (default 0 = full)
#   WORK=/workspace
set -euo pipefail

WORK="${WORK:-/workspace}"
MODELS="${MODELS:-qwen3 lfm2 hermes3 gpt2}"
MAX_TOKENS="${MAX_TOKENS:-0}"
OUT="$WORK/nl_eval_results"
export HF_HOME="${HF_HOME:-$WORK/hf_cache}"
HERE="$(cd "$(dirname "$0")" && pwd)"

[ -n "${HF_TOKEN:-}" ] || { echo "HF_TOKEN is not set"; exit 1; }

# transformers rejects huggingface_hub 2.x; the upper bound is load-bearing.
pip install --quiet "huggingface_hub>=1.5.0,<2.0" transformers accelerate datasets tqdm \
  || pip install --quiet --break-system-packages "huggingface_hub>=1.5.0,<2.0" transformers accelerate datasets tqdm

base_of() {
  case "$1" in
    qwen3)   echo "Qwen/Qwen3-0.6B-Base" ;;
    lfm2)    echo "LiquidAI/LFM2.5-1.2B-Base" ;;
    hermes3) echo "NousResearch/Hermes-3-Llama-3.2-3B" ;;
    gpt2)    echo "openai-community/gpt2-medium" ;;
    *) echo "unknown model $1" >&2; exit 1 ;;
  esac
}

mkdir -p "$OUT"
: > "$OUT/summary.tsv"
echo -e "name\tbase_ppl\ttuned_ppl\tratio\tbase_trivia\ttuned_trivia" >> "$OUT/summary.tsv"

for m in $MODELS; do
  python "$HERE/nl_integrity_eval.py" \
    --base  "$(base_of "$m")" \
    --tuned "prompterminal/fdm-40ch-fresh-${m}-model" \
    --name  "$m" --out "$OUT" --max-tokens "$MAX_TOKENS" \
    2>&1 | tee "$OUT/$m.log"
done

echo
echo "================ SUMMARY ================"
column -t -s $'\t' "$OUT/summary.tsv"
