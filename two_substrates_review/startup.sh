#!/usr/bin/env bash
# =============================================================================
# run_two_substrates_review.sh  --  end-to-end disjoint split-source experiment
#
# What it does (each stage can be switched off, see the env vars below):
#   0. preflight       GPU, HF token, sibling scripts present
#   1. dependencies    pinned pip installs (huggingface_hub must stay <2.0)
#   2. encoder         clone FDM_PARAMETRIC, apply the active_channels patch (idempotent)
#   3. host model      download the two-block checkpoint from HuggingFace, check dims
#   4. sanity          host decodes all carriers at position 513 (gate: B slot >= 95%)
#   5. masked baseline host on masked blocks, no prefix, no training (the shift test)
#   6. training        write head per split and seed, matched + shuffled-prefix control
#   7. summary         table across seeds/splits
#   8. upload          results -> private HF dataset repo, heads -> private HF model repo
#
# Usage (run inside tmux so it survives an SSH drop):
#   export HF_TOKEN=hf_xxx
#   tmux new -s fdm
#   bash run_two_substrates_review.sh
#
# Common overrides (all optional):
#   MODEL=qwen3|hermes3        default qwen3
#   SEEDS="1 2 3"              default "1"
#   SPLITS="4 8"               number of prefix-only channels; default "4 8"
#   STEPS_4=5000  STEPS_8PLUS=15000   write-head steps for split 4 / for splits >= 8
#   N_EVAL=100                 samples per eval (use 200 for final numbers)
#   PARTITION=interleaved|contiguous
#   MASKED_SPLITS="4,8,16"     splits for the masked-baseline stage
#   RUN_SANITY=0 RUN_MASKED=0 RUN_TRAIN=0 UPLOAD=0   skip stages
#   SKIP_DONE=1                skip a split whose results JSON already exists (default 1)
#   WORK=/workspace           root directory
#   DRY_RUN=1                  print the commands instead of running them
#
# Not done here on purpose: pushing to GitHub. The repo is attributed to a personal
# account; anything reviewer-facing must go to the anonymous account instead.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${WORK:-/workspace}"
MODEL="${MODEL:-qwen3}"
SEEDS="${SEEDS:-1}"
SPLITS="${SPLITS:-4 8}"
N_EVAL="${N_EVAL:-100}"
STEPS_4="${STEPS_4:-5000}"
STEPS_8PLUS="${STEPS_8PLUS:-15000}"
PARTITION="${PARTITION:-interleaved}"
MASKED_SPLITS="${MASKED_SPLITS:-4,8,16}"
RUN_SANITY="${RUN_SANITY:-1}"
RUN_MASKED="${RUN_MASKED:-1}"
RUN_TRAIN="${RUN_TRAIN:-1}"
UPLOAD="${UPLOAD:-1}"
SKIP_DONE="${SKIP_DONE:-1}"
DRY_RUN="${DRY_RUN:-0}"
RESULTS_REPO="${RESULTS_REPO:-prompterminal/fdm-two-substrates-review}"
HEADS_REPO="${HEADS_REPO:-prompterminal/fdm-two-substrates-heads}"

case "$MODEL" in
  qwen3)   MODEL_REPO="prompterminal/fdm-40ch-two-block-qwen3";          VOCAB=151936 ;;
  hermes3) MODEL_REPO="prompterminal/fdm-40ch-two-block-hermes3-correct"; VOCAB=128256 ;;
  *) echo "MODEL must be qwen3 or hermes3 (got '$MODEL')" >&2; exit 1 ;;
esac
# VOCAB must equal the vocab_size the checkpoint's encoder was built with
# (nhop_source token_map = rng.choice(vocab_size, 64)); values come from
# fdm_two_block_training.py (Qwen3) and fdm_two_block_training_hermes3.py.

MODEL_DIR="$WORK/FDM_IN_WEIGHTS/two_block_$MODEL"
OUT="$WORK/FDM_IN_WEIGHTS/two_substrates_review/$MODEL"
PARAM_DIR="$WORK/FDM_PARAMETRIC"
SWEEP="$SCRIPT_DIR/split_ratio_sweep_disjoint.py"
PATCH="$SCRIPT_DIR/patch_nhop_source.py"

export HF_HOME="${HF_HOME:-$WORK/hf_cache}"
export PYTHONPATH="$PARAM_DIR:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

if [ "$DRY_RUN" = 1 ]; then PY="echo [dry-run] python"; PIP="echo [dry-run] pip"; else PY="python"; PIP="pip"; fi

mkdir -p "$OUT"
exec > >(tee -a "$OUT/run.log") 2>&1

log()  { printf '\n[%s] === %s\n' "$(date +%H:%M:%S)" "$*"; }
die()  { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
trap 'printf "\nFAILED at line %s (exit %s). Log: %s\n" "$LINENO" "$?" "$OUT/run.log" >&2' ERR

# --------------------------------------------------------------------------- 0
log "0. preflight  (model=$MODEL vocab=$VOCAB seeds=[$SEEDS] splits=[$SPLITS] n_eval=$N_EVAL partition=$PARTITION)"
[ -f "$SWEEP" ] || die "missing $SWEEP (keep this script next to split_ratio_sweep_disjoint.py)"
[ -f "$PATCH" ] || die "missing $PATCH (keep this script next to patch_nhop_source.py)"
if [ "$DRY_RUN" != 1 ]; then
  [ -n "${HF_TOKEN:-}" ] || die "HF_TOKEN is not set (export HF_TOKEN=hf_...)"
  command -v nvidia-smi >/dev/null || die "no GPU driver found (nvidia-smi missing)"
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
fi

# --------------------------------------------------------------------------- 1
log "1. dependencies"
# transformers rejects huggingface_hub 2.x, so the pin is load-bearing.
$PIP install --quiet "huggingface_hub>=1.5.0,<2.0" tqdm numpy accelerate transformers \
  || $PIP install --quiet --break-system-packages "huggingface_hub>=1.5.0,<2.0" tqdm numpy accelerate transformers
if [ "$DRY_RUN" != 1 ]; then
  python - <<'EOF'
import transformers, huggingface_hub, torch
print("transformers", transformers.__version__, "| huggingface_hub", huggingface_hub.__version__,
      "| torch", torch.__version__, "| cuda", torch.cuda.is_available())
assert torch.cuda.is_available(), "CUDA not available to torch"
from huggingface_hub import HfApi
print("HF user:", HfApi().whoami()["name"])
EOF
fi

# --------------------------------------------------------------------------- 2
log "2. encoder (FDM_PARAMETRIC + active_channels patch)"
if [ ! -f "$PARAM_DIR/nhop_source.py" ]; then
  git clone --depth 1 https://github.com/jeannemtl/FDM_PARAMETRIC.git "$PARAM_DIR"
fi
if [ "$DRY_RUN" = 1 ]; then
  echo "[dry-run] python $PATCH $PARAM_DIR/nhop_source.py"
else
  python "$PATCH" "$PARAM_DIR/nhop_source.py"
  python - <<'EOF'
import inspect, nhop_source
sig = inspect.signature(nhop_source.TurboFDMSignalEncoder.encode_memory)
print("encode_memory", sig)
assert "active_channels" in sig.parameters, "encoder patch missing"
EOF
fi

# --------------------------------------------------------------------------- 3
log "3. host checkpoint  ($MODEL_REPO -> $MODEL_DIR)"
if [ -f "$MODEL_DIR/config.json" ]; then
  echo "already downloaded, skipping"
else
  mkdir -p "$MODEL_DIR"
  $PY - <<EOF
from huggingface_hub import snapshot_download
snapshot_download(repo_id="$MODEL_REPO", local_dir="$MODEL_DIR")
print("downloaded $MODEL_REPO")
EOF
fi
if [ "$DRY_RUN" != 1 ]; then
  python - <<EOF
import json
c = json.load(open("$MODEL_DIR/config.json"))
L = c.get("num_hidden_layers"); kv = c.get("num_key_value_heads")
hd = c.get("head_dim") or c["hidden_size"] // c["num_attention_heads"]
print(f"layers={L} kv_heads={kv} head_dim={hd} vocab_in_config={c.get('vocab_size')}")
assert (L, kv, hd) == (28, 8, 128), (
    "write head is hard-coded for 28 layers / 8 KV heads / head_dim 128; "
    "edit CrossAttentionWriteHead in split_ratio_sweep_disjoint.py for this model")
EOF
fi

COMMON=(--model "$MODEL_DIR" --vocab_size "$VOCAB" --partition "$PARTITION")

# --------------------------------------------------------------------------- 4
if [ "$RUN_SANITY" = 1 ]; then
  log "4. sanity: host decodes all carriers (expect B slot ~99%)"
  $PY -u "$SWEEP" "${COMMON[@]}" --output_dir "$OUT/sanity" --splits 0 --n_eval 50 --seed 42
  if [ "$DRY_RUN" != 1 ]; then
    python - <<EOF
import json, sys
r = json.load(open("$OUT/sanity/sweep_results_seed42.json"))[0]
b = r["block_b_acc_slot"]
print(f"sanity B slot accuracy: {b*100:.1f}%")
if b < 0.95:
    sys.exit("Sanity gate failed (<95%): checkpoint and encoder settings do not match. "
             "Check vocab_size and the encoder args in make_encoder().")
EOF
  fi
fi

# --------------------------------------------------------------------------- 5
if [ "$RUN_MASKED" = 1 ]; then
  log "5. masked-block baseline (no prefix, no training): host shift test"
  if [ "$SKIP_DONE" = 1 ] && [ -f "$OUT/masked/ctx_only_masked_seed1.json" ]; then
    echo "already done, skipping"
  else
    $PY -u "$SWEEP" "${COMMON[@]}" --output_dir "$OUT/masked" --ctx_only_masked \
        --splits "$MASKED_SPLITS" --n_eval "$N_EVAL" --seed 1
  fi
fi

# --------------------------------------------------------------------------- 6
steps_for() { if [ "$1" -le 4 ]; then echo "$STEPS_4"; else echo "$STEPS_8PLUS"; fi; }

if [ "$RUN_TRAIN" = 1 ]; then
  for SEED in $SEEDS; do
    for N in $SPLITS; do
      D="$OUT/seed$SEED/split$N"
      STEPS="$(steps_for "$N")"
      log "6. train  seed=$SEED  prefix-only channels=$N  steps=$STEPS  -> $D"
      if [ "$SKIP_DONE" = 1 ] && [ -f "$D/sweep_results_seed$SEED.json" ]; then
        echo "already done, skipping"; continue
      fi
      mkdir -p "$D"
      # one process per split so each split gets its own results JSON and head checkpoint
      $PY -u "$SWEEP" "${COMMON[@]}" --output_dir "$D" --splits "$N" \
          --n_steps "$STEPS" --n_eval "$N_EVAL" --seed "$SEED"
    done
  done
fi

# --------------------------------------------------------------------------- 7
log "7. summary"
if [ "$DRY_RUN" != 1 ]; then
  python - <<EOF
import glob, json, os
rows = []
for f in sorted(glob.glob("$OUT/seed*/split*/sweep_results_seed*.json")):
    for r in json.load(open(f)):
        c = r.get("control_shuffled_prefix", {})
        rows.append((r.get("seed"), r["n_param"], r["n_ctx"],
                     r["block_a_acc_slot"], c.get("block_a_acc_slot", float("nan")),
                     r["block_b_acc_slot"], c.get("block_b_acc_slot", float("nan")),
                     r.get("frac_answers_with_repeated_names", float("nan")),
                     c.get("frac_answers_with_repeated_names", float("nan")),
                     r["n_samples"]))
if not rows:
    print("no trained results found")
else:
    print(f"{'seed':>4} {'A':>3} {'B':>3} | {'A match':>8} {'A ctrl':>7} {'delta':>6} | {'B match':>8} {'B ctrl':>7} | "
          f"{'rep m':>6} {'rep c':>6} | n")
    for s, a, b, am, ac, bm, bc, rm, rc, n in rows:
        print(f"{s:>4} {a:>3} {b:>3} | {am*100:7.1f}% {ac*100:6.1f}% {(am-ac)*100:5.1f} | "
              f"{bm*100:7.1f}% {bc*100:6.1f}% | {rm*100:5.0f}% {rc*100:5.0f}% | {n}")
    print("\nA delta = matched minus shuffled-prefix control; report this, not the 1/M chance level.")
for f in sorted(glob.glob("$OUT/masked/ctx_only_masked_seed*.json")):
    print("\nmasked baseline:", os.path.relpath(f, "$OUT"))
    for r in json.load(open(f)):
        print(f"  {r['n_param']:>2} removed: B slot {r['block_b_acc_slot']*100:5.1f}%   A slot {r['block_a_acc_slot']*100:5.1f}%")
EOF
fi

# --------------------------------------------------------------------------- 8
if [ "$UPLOAD" = 1 ]; then
  log "8. upload to HuggingFace (private): results -> $RESULTS_REPO, heads -> $HEADS_REPO"
  $PY - <<EOF
from huggingface_hub import HfApi
api = HfApi()
api.create_repo("$RESULTS_REPO", repo_type="dataset", private=True, exist_ok=True)
api.upload_folder(repo_id="$RESULTS_REPO", repo_type="dataset", folder_path="$OUT",
                  path_in_repo="$MODEL", ignore_patterns=["*.pt"],
                  commit_message="two_substrates_review: $MODEL results")
api.create_repo("$HEADS_REPO", repo_type="model", private=True, exist_ok=True)
api.upload_folder(repo_id="$HEADS_REPO", repo_type="model", folder_path="$OUT",
                  path_in_repo="$MODEL", allow_patterns=["*.pt"],
                  commit_message="two_substrates_review: $MODEL write heads")
print("uploaded")
EOF
fi

log "done. results in $OUT  (log: $OUT/run.log)"
