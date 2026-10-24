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
#   SET=fresh|twoblock|mixed which fine-tuned checkpoints to test (default fresh)
#                            twoblock covers qwen3 and hermes3 only
#                            mixed = the four 10-channel mixed-domain models in
#                            prompterminal/fdm-mixed-domain-10ch (paper section 3.3)
#   TUNED=org/repo           test one arbitrary checkpoint; MODELS must then be
#                            a single tag naming its base (e.g. MODELS=qwen3)
#   TUNED_SUBFOLDER=dir      folder inside TUNED that holds config.json + weights
#                            (e.g. phase2_final when the repo root is empty)
#   MAX_TOKENS=20000         quick run on the first N WikiText tokens (default 0 = full)
#   WORK=/workspace
set -euo pipefail

WORK="${WORK:-/workspace}"
SET="${SET:-fresh}"
if [ -n "${TUNED:-}" ]; then
  MODELS="${MODELS:?set MODELS to the single base tag for TUNED}"
elif [ "$SET" = "twoblock" ]; then
  MODELS="${MODELS:-qwen3 hermes3}"
elif [ "$SET" = "mixed" ]; then
  MODELS="${MODELS:-qwen3 lfm2 hermes3 gpt2}"
else
  MODELS="${MODELS:-qwen3 lfm2 hermes3 gpt2}"
fi
MAX_TOKENS="${MAX_TOKENS:-0}"
OUT="${OUT:-$WORK/nl_eval_results_$SET}"
export HF_HOME="${HF_HOME:-$WORK/hf_cache}"
HERE="$(cd "$(dirname "$0")" && pwd)"

[ -n "${HF_TOKEN:-}" ] || { echo "HF_TOKEN is not set"; exit 1; }

# transformers rejects huggingface_hub 2.x; the upper bound is load-bearing.
pip install --quiet "huggingface_hub>=1.5.0,<2.0" transformers accelerate datasets tqdm sentencepiece protobuf \
  || pip install --quiet --break-system-packages "huggingface_hub>=1.5.0,<2.0" transformers accelerate datasets tqdm sentencepiece protobuf

base_of() {
  case "$1" in
    qwen3)   echo "Qwen/Qwen3-0.6B-Base" ;;
    lfm2)    echo "LiquidAI/LFM2.5-1.2B-Base" ;;
    hermes3) echo "NousResearch/Hermes-3-Llama-3.2-3B" ;;
    gpt2)    echo "openai-community/gpt2-medium" ;;
    *) echo "unknown model $1" >&2; exit 1 ;;
  esac
}

tuned_of() {
  if [ -n "${TUNED:-}" ]; then echo "$TUNED"; return; fi
  case "$SET:$1" in
    fresh:*)          echo "prompterminal/fdm-40ch-fresh-$1-model" ;;
    twoblock:qwen3)   echo "prompterminal/fdm-40ch-two-block-qwen3" ;;
    twoblock:hermes3) echo "prompterminal/fdm-40ch-two-block-hermes3-correct" ;;
    mixed:*)          echo "prompterminal/fdm-mixed-domain-10ch" ;;
    *) echo "no $SET checkpoint known for $1 (pass TUNED=org/repo)" >&2; exit 1 ;;
  esac
}

# Folder inside the tuned repo that holds the checkpoint ("" = repo root).
subfolder_of() {
  if [ -n "${TUNED_SUBFOLDER:-}" ]; then echo "$TUNED_SUBFOLDER"; return; fi
  if [ "$SET" = "mixed" ]; then
    case "$1" in
      qwen3)   echo "qwen3-0.6b" ;;
      lfm2)    echo "lfm2.5-1.2b" ;;
      hermes3) echo "hermes3-3b" ;;
      gpt2)    echo "gpt2-medium" ;;
    esac
  fi
}

mkdir -p "$OUT"
: > "$OUT/summary.tsv"
echo -e "name\tbase_ppl\ttuned_ppl\tratio\tbase_trivia\ttuned_trivia\tbase_leak\ttuned_leak\tbase_word+leak\ttuned_word+leak" >> "$OUT/summary.tsv"

for m in $MODELS; do
  SUB="$(subfolder_of "$m")"
  python "$HERE/nl_integrity_eval.py" \
    --base  "$(base_of "$m")" \
    --tuned "$(tuned_of "$m")" \
    --name  "$m" --out "$OUT" --max-tokens "$MAX_TOKENS" \
    ${SUB:+--tuned-subfolder "$SUB"} \
    2>&1 | tee "$OUT/$m.log"
done

echo
echo "================ SUMMARY ================"
awk -F'\t' '{printf "%-8s %14s %16s %14s %12s %12s %10s %10s %15s %15s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10}' "$OUT/summary.tsv"
